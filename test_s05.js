/**
 * S05テンプレート 4段階テスト
 * HANDOVER_tmpl_next50_S05.md 準拠
 * Stage1: 起動 / Stage2: ゲームプレイ状態 / Stage3: 状態注入でCLEAR発火 / Stage4: 実操作
 */
const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const TEMPLATES = [
    'tmpl_sugoroku',
    'tmpl_kanji_quiz',
    'tmpl_tanabata_wish',
    'tmpl_yoyo_skill',
    'tmpl_taiko_rhythm',
    'tmpl_origami_puzzle',
    'tmpl_shogi_lite',
    'tmpl_pachinko_lite',
    'tmpl_hanafuda',
    'tmpl_mahjong_game',
];

const BASE = 'file://' + path.resolve(__dirname);

const results = [];

async function test(name, fn) {
    try {
        await fn();
        results.push({ name, status: 'PASS' });
        console.log('✅ PASS:', name);
    } catch (e) {
        results.push({ name, status: 'FAIL', error: e.message });
        console.log('❌ FAIL:', name, '-', e.message);
    }
}

(async () => {
    const browser = await chromium.launch({ headless: true });
    const ctx = await browser.newContext();

    const errors = {};

    for (const tmpl of TEMPLATES) {
        const page = await ctx.newPage();
        const jsErrors = [];
        page.on('pageerror', e => jsErrors.push(e.message));

        const url = `${BASE}/${tmpl}.html`;
        console.log('\n--- Testing:', tmpl, '---');

        try {
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 10000 });

            // Stage 1: Launch — click START, no JS errors
            await test(`[${tmpl}] Stage1: 起動`, async () => {
                const btn = page.locator('button:has-text("START")').first();
                await btn.waitFor({ timeout: 5000 });
                await btn.click();
                await page.waitForTimeout(300);
                const running = await page.evaluate(() => {
                    return typeof gameState !== 'undefined' && gameState.running === true;
                });
                if (!running) throw new Error('gameState.running が true にならない');
                if (jsErrors.length > 0) throw new Error('JS エラー: ' + jsErrors.join(', '));
            });

            // Stage 2: Gameplay state verification
            await test(`[${tmpl}] Stage2: ゲームプレイ状態`, async () => {
                const stateOk = await page.evaluate((t) => {
                    if (!gameState.running) return false;
                    // Per-template checks
                    switch(t) {
                        case 'tmpl_sugoroku':
                            return gameState.pos === 0;
                        case 'tmpl_kanji_quiz':
                            return gameState.qIdx === 0 && gameState.correct === 0;
                        case 'tmpl_tanabata_wish':
                            return gameState.wishCount === 0;
                        case 'tmpl_yoyo_skill':
                            return gameState.phase === 'swinging' || gameState.successCount === 0;
                        case 'tmpl_taiko_rhythm':
                            return gameState.hits === 0;
                        case 'tmpl_origami_puzzle':
                            return gameState.currentStep === 0;
                        case 'tmpl_shogi_lite':
                            return gameState.board !== null && gameState.turn === 0;
                        case 'tmpl_pachinko_lite':
                            return gameState.ballsUsed === 0;
                        case 'tmpl_hanafuda':
                            return gameState.playerHand && gameState.playerHand.length === 8;
                        case 'tmpl_mahjong_game':
                            return gameState.hand && gameState.hand.length === 14;
                        default:
                            return true;
                    }
                }, tmpl);
                if (!stateOk) throw new Error('ゲームプレイ状態が想定外');
            });

            // Stage 3: CLEAR state injection
            await test(`[${tmpl}] Stage3: 状態注入でCLEAR発火`, async () => {
                await page.evaluate((t) => {
                    switch(t) {
                        case 'tmpl_sugoroku':
                            gameState.pos = 27;
                            break;
                        case 'tmpl_kanji_quiz':
                            gameState.qIdx = 10;
                            gameState.correct = 10;
                            endQuiz();
                            return;
                        case 'tmpl_tanabata_wish':
                            gameState.wishCount = 4;
                            gameState.running = true;
                            break;
                        case 'tmpl_yoyo_skill':
                            gameState.successCount = 6;
                            break;
                        case 'tmpl_taiko_rhythm':
                            gameState.hits = 32;
                            gameState.spawnIdx = 32;
                            gameState.activeNotes = [];
                            endGame();
                            return;
                        case 'tmpl_origami_puzzle':
                            gameState.completedSteps = 4;
                            gameState.currentStep = 5;
                            clearGame();
                            return;
                        case 'tmpl_shogi_lite':
                            gameState.board[0][4] = null; // Remove cpu king
                            checkEndCondition();
                            return;
                        case 'tmpl_pachinko_lite':
                            gameState.jackpotGauge = 99;
                            gameState.balls.push({x:192+22, y:560, vx:0, vy:1, active:true, trail:[]});
                            break;
                        case 'tmpl_hanafuda':
                            gameState.running = false;
                            gameState.playerPoints = 10;
                            clearGame();
                            return;
                        case 'tmpl_mahjong_game':
                            gameState.winCount = 4;
                            clearGame();
                            return;
                    }
                }, tmpl);
                await page.waitForTimeout(800);

                const cleared = await page.evaluate(() => {
                    const cs = document.getElementById('clearScreen');
                    if (!cs) return false;
                    return cs.style.display === 'flex' || cs.style.display === 'block';
                });
                if (!cleared) throw new Error('clearScreenが表示されない');
            });

            // Stage 3b: RETRY復帰チェック
            await test(`[${tmpl}] Stage3b: RETRY復帰`, async () => {
                const retryBtn = page.locator('#clearScreen button, .screen button').first();
                await retryBtn.click();
                await page.waitForTimeout(200);
                const startVisible = await page.evaluate(() => {
                    const ss = document.getElementById('startScreen');
                    if (!ss) return false;
                    return ss.style.display === 'flex' || ss.style.display === 'block';
                });
                if (!startVisible) throw new Error('startScreenに戻らない');
            });

        } catch (e) {
            results.push({ name: `[${tmpl}] 全体エラー`, status: 'FAIL', error: e.message });
            console.log('❌ 全体エラー:', tmpl, e.message);
        }

        errors[tmpl] = [...jsErrors];
        await page.close();
    }

    // Stage 4 spot checks (real operations)
    console.log('\n--- Stage4: 実操作テスト ---');

    // sugoroku: roll dice and check pos changes
    const page4 = await ctx.newPage();
    await page4.goto(`${BASE}/tmpl_sugoroku.html`, { waitUntil: 'domcontentloaded' });
    await page4.locator('button:has-text("START")').first().click();
    await page4.waitForTimeout(200);
    await test('[sugoroku] Stage4: サイコロ実操作', async () => {
        const posBefore = await page4.evaluate(() => gameState.pos);
        await page4.evaluate(() => rollDice());
        await page4.waitForTimeout(1500);
        const posAfter = await page4.evaluate(() => gameState.pos);
        if (posAfter === posBefore) throw new Error('pos が変化しない');
    });
    await page4.close();

    // kanji_quiz: answer a question
    const page4b = await ctx.newPage();
    await page4b.goto(`${BASE}/tmpl_kanji_quiz.html`, { waitUntil: 'domcontentloaded' });
    await page4b.locator('button:has-text("START")').first().click();
    await page4b.waitForTimeout(200);
    await test('[kanji_quiz] Stage4: 回答実操作', async () => {
        const before = await page4b.evaluate(() => gameState.qIdx);
        await page4b.evaluate(() => answer(0));
        await page4b.waitForTimeout(1500);
        const after = await page4b.evaluate(() => gameState.qIdx + gameState.correct + gameState.wrong);
        if (after <= before) throw new Error('回答後状態が変化しない');
    });
    await page4b.close();

    // tanabata_wish: send a wish
    const page4c = await ctx.newPage();
    await page4c.goto(`${BASE}/tmpl_tanabata_wish.html`, { waitUntil: 'domcontentloaded' });
    await page4c.locator('button:has-text("START")').first().click();
    await page4c.waitForTimeout(200);
    await test('[tanabata_wish] Stage4: 短冊送信実操作', async () => {
        await page4c.fill('#wishInput', 'テスト願い事');
        await page4c.evaluate(() => sendWish());
        await page4c.waitForTimeout(500);
        const count = await page4c.evaluate(() => gameState.wishCount);
        if (count !== 1) throw new Error('wishCount が 1 にならない（実際: ' + count + '）');
    });
    await page4c.close();

    // origami_puzzle: click steps in order
    const page4d = await ctx.newPage();
    await page4d.goto(`${BASE}/tmpl_origami_puzzle.html`, { waitUntil: 'domcontentloaded' });
    await page4d.locator('button:has-text("START")').first().click();
    await page4d.waitForTimeout(200);
    await test('[origami_puzzle] Stage4: 手順順番クリック', async () => {
        await page4d.evaluate(() => clickStep(0));
        await page4d.waitForTimeout(600);
        const step = await page4d.evaluate(() => gameState.currentStep);
        if (step !== 1) throw new Error('Step1後にcurrentStepが1にならない（実際: ' + step + '）');
    });
    await page4d.close();

    // shogi_lite: verify getMoves returns valid moves
    const page4e = await ctx.newPage();
    await page4e.goto(`${BASE}/tmpl_shogi_lite.html`, { waitUntil: 'domcontentloaded' });
    await page4e.locator('button:has-text("START")').first().click();
    await page4e.waitForTimeout(200);
    await test('[shogi_lite] Stage4: 駒移動可能判定', async () => {
        const moves = await page4e.evaluate(() => {
            // Player king is at row 4, col 0
            return getMoves(gameState.board, 4, 0);
        });
        if (!Array.isArray(moves) || moves.length === 0) throw new Error('王の移動可能マスが0');
    });
    await page4e.close();

    // hanafuda: verify field match detection
    const page4f = await ctx.newPage();
    await page4f.goto(`${BASE}/tmpl_hanafuda.html`, { waitUntil: 'domcontentloaded' });
    await page4f.locator('button:has-text("START")').first().click();
    await page4f.waitForTimeout(200);
    await test('[hanafuda] Stage4: こいこい役判定ロジック', async () => {
        // Inject captures with sanko (3 hikari) and verify yaku detection
        const yakuFound = await page4f.evaluate(() => {
            const testCaptures = [0, 8, 28]; // 松に鶴(hikari), 桜に幕(hikari), 芒に月(hikari)
            const yaku = checkYaku(testCaptures);
            return yaku.some(y => y.name === '三光');
        });
        if (!yakuFound) throw new Error('三光役が検出されない（役判定ロジック異常）');
    });
    await page4f.close();

    // mahjong_game: verify complete hand detection
    const page4g = await ctx.newPage();
    await page4g.goto(`${BASE}/tmpl_mahjong_game.html`, { waitUntil: 'domcontentloaded' });
    await page4g.locator('button:has-text("START")').first().click();
    await page4g.waitForTimeout(200);
    await test('[mahjong_game] Stage4: 和了判定ロジック', async () => {
        const result = await page4g.evaluate(() => {
            // Standard winning hand: 1m1m1m 2m3m4m 5m6m7m 1p1p1p 2p2p
            const winHand = [
                {suit:'m',n:1},{suit:'m',n:1},{suit:'m',n:1},
                {suit:'m',n:2},{suit:'m',n:3},{suit:'m',n:4},
                {suit:'m',n:5},{suit:'m',n:6},{suit:'m',n:7},
                {suit:'p',n:1},{suit:'p',n:1},{suit:'p',n:1},
                {suit:'p',n:2},{suit:'p',n:2},
            ];
            return checkWin(winHand);
        });
        if (!result) throw new Error('標準的な和了形が検出されない（和了判定ロジック異常）');
    });
    await page4g.close();

    await browser.close();

    // Summary
    console.log('\n========== S05 テスト結果 ==========');
    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    console.log(`合格: ${passed} / ${passed + failed}`);
    results.forEach(r => {
        const icon = r.status === 'PASS' ? '✅' : '❌';
        console.log(`${icon} ${r.name}${r.error ? ' → ' + r.error : ''}`);
    });

    // JS error report
    console.log('\n--- JSエラー一覧 ---');
    for (const [tmpl, errs] of Object.entries(errors)) {
        if (errs.length > 0) console.log('  ' + tmpl + ':', errs.join(', '));
    }
    if (Object.values(errors).every(e => e.length === 0)) {
        console.log('  JSエラーなし ✅');
    }

    const killList = TEMPLATES.filter(t => {
        const tResults = results.filter(r => r.name.startsWith('[' + t + ']'));
        return tResults.some(r => r.status === 'FAIL');
    });
    if (killList.length > 0) {
        console.log('\n⚠️  KILL候補:', killList.join(', '));
    } else {
        console.log('\n🎉 全テンプレート合格！');
    }
})();
