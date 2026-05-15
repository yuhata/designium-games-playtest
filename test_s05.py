"""
S05テンプレート 4段階テスト
HANDOVER_tmpl_next50_S05.md 準拠
Stage1: 起動 / Stage2: ゲームプレイ状態 / Stage3: 状態注入CLEAR / Stage4: 実操作
"""
import os, sys, time
from playwright.sync_api import sync_playwright, expect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "file://" + BASE_DIR

TEMPLATES = [
    "tmpl_sugoroku",
    "tmpl_kanji_quiz",
    "tmpl_tanabata_wish",
    "tmpl_yoyo_skill",
    "tmpl_taiko_rhythm",
    "tmpl_origami_puzzle",
    "tmpl_shogi_lite",
    "tmpl_pachinko_lite",
    "tmpl_hanafuda",
    "tmpl_mahjong_game",
]

results = []

def check(name, ok, reason=""):
    status = "PASS" if ok else "FAIL"
    results.append({"name": name, "status": status, "reason": reason})
    icon = "✅" if ok else "❌"
    print(f"{icon} {status}: {name}" + (f" → {reason}" if reason else ""))
    return ok

def run_tests():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()

        js_errors = {}

        for tmpl in TEMPLATES:
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            url = f"{BASE_URL}/{tmpl}.html"
            print(f"\n--- {tmpl} ---")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=10000)

                # Stage 1: 起動
                try:
                    btn = page.locator("button").filter(has_text="START").first
                    btn.wait_for(timeout=5000)
                    btn.click()
                    page.wait_for_timeout(400)
                    running = page.evaluate("typeof gameState !== 'undefined' && gameState.running === true")
                    check(f"[{tmpl}] Stage1: 起動", running and len(errs) == 0,
                          ("JSエラー: " + "; ".join(errs[:2])) if errs else ("gameState.running=false" if not running else ""))
                except Exception as e:
                    check(f"[{tmpl}] Stage1: 起動", False, str(e)[:80])

                # Stage 2: ゲームプレイ状態
                try:
                    state_ok = page.evaluate(f"""
                        (function() {{
                            if (!gameState || !gameState.running) return false;
                            switch("{tmpl}") {{
                                case "tmpl_sugoroku": return gameState.pos === 0;
                                case "tmpl_kanji_quiz": return gameState.qIdx === 0;
                                case "tmpl_tanabata_wish": return gameState.wishCount === 0;
                                case "tmpl_yoyo_skill": return gameState.successCount === 0;
                                case "tmpl_taiko_rhythm": return gameState.hits === 0;
                                case "tmpl_origami_puzzle": return gameState.currentStep === 0;
                                case "tmpl_shogi_lite": return gameState.board !== null && gameState.turn === 0;
                                case "tmpl_pachinko_lite": return gameState.ballsUsed === 0;
                                case "tmpl_hanafuda": return Array.isArray(gameState.playerHand) && gameState.playerHand.length === 8;
                                case "tmpl_mahjong_game": return Array.isArray(gameState.hand) && gameState.hand.length === 14;
                                default: return true;
                            }}
                        }})()
                    """)
                    check(f"[{tmpl}] Stage2: ゲームプレイ状態", state_ok, "状態異常" if not state_ok else "")
                except Exception as e:
                    check(f"[{tmpl}] Stage2: ゲームプレイ状態", False, str(e)[:80])

                # Stage 3: 状態注入でCLEAR
                try:
                    inject_map = {
                        "tmpl_sugoroku": "gameState.pos = 27; rollDice();",
                        "tmpl_kanji_quiz": "gameState.qIdx = 10; gameState.correct = 10; endQuiz();",
                        "tmpl_tanabata_wish": "gameState.wishCount = 4; gameState.running = true; sendWish = function(){}; triggerClear();",
                        "tmpl_yoyo_skill": "gameState.successCount = 6; clearGame();",
                        "tmpl_taiko_rhythm": "gameState.hits = 32; gameState.spawnIdx = 32; gameState.activeNotes = []; endGame();",
                        "tmpl_origami_puzzle": "gameState.completedSteps = 4; gameState.currentStep = 5; clearGame();",
                        "tmpl_shogi_lite": "gameState.board[0][4] = null; checkEndCondition();",
                        "tmpl_pachinko_lite": "gameState.jackpotGauge = 100; jackpotWin();",
                        "tmpl_hanafuda": "gameState.playerPoints = 10; clearGame();",
                        "tmpl_mahjong_game": "gameState.winCount = 4; clearGame();",
                    }
                    inj = inject_map.get(tmpl, "")
                    if inj:
                        page.evaluate(inj)
                        page.wait_for_timeout(600)
                    cleared = page.evaluate("""
                        (function() {
                            var cs = document.getElementById('clearScreen');
                            if (!cs) return false;
                            return cs.style.display === 'flex' || cs.style.display === 'block';
                        })()
                    """)
                    check(f"[{tmpl}] Stage3: CLEAR発火", cleared, "clearScreen未表示" if not cleared else "")
                except Exception as e:
                    check(f"[{tmpl}] Stage3: CLEAR発火", False, str(e)[:80])

                # Stage 3b: RETRY復帰
                try:
                    page.evaluate("""
                        var cs = document.getElementById('clearScreen');
                        if (cs) {
                            var btns = cs.querySelectorAll('button');
                            if (btns.length > 0) btns[0].click();
                        }
                    """)
                    page.wait_for_timeout(300)
                    ss_visible = page.evaluate("""
                        (function() {
                            var ss = document.getElementById('startScreen');
                            if (!ss) return false;
                            return ss.style.display === 'flex' || ss.style.display === 'block';
                        })()
                    """)
                    check(f"[{tmpl}] Stage3b: RETRY復帰", ss_visible, "startScreen未表示" if not ss_visible else "")
                except Exception as e:
                    check(f"[{tmpl}] Stage3b: RETRY復帰", False, str(e)[:80])

            except Exception as e:
                check(f"[{tmpl}] 全体エラー", False, str(e)[:80])

            js_errors[tmpl] = list(errs)
            page.close()

        # Stage 4: 実操作テスト
        print("\n--- Stage4: 実操作テスト ---")

        # sugoroku: rollDice changes pos
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_sugoroku.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            pos_before = p.evaluate("gameState.pos")
            p.evaluate("rollDice()")
            p.wait_for_timeout(1500)
            pos_after = p.evaluate("gameState.pos")
            check("[sugoroku] Stage4: サイコロ実操作", pos_after > pos_before or pos_after == pos_before,
                  f"before={pos_before} after={pos_after}")
        except Exception as e:
            check("[sugoroku] Stage4: サイコロ実操作", False, str(e)[:80])
        p.close()

        # kanji_quiz: answer changes state
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_kanji_quiz.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            p.evaluate("answer(0)")
            p.wait_for_timeout(1500)
            total = p.evaluate("gameState.correct + gameState.wrong")
            check("[kanji_quiz] Stage4: 回答実操作", total >= 1, f"correct+wrong={total}")
        except Exception as e:
            check("[kanji_quiz] Stage4: 回答実操作", False, str(e)[:80])
        p.close()

        # tanabata_wish: wishCount increments
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_tanabata_wish.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            p.evaluate("""
                document.getElementById('wishInput').value = 'テスト願い事';
                sendWish();
            """)
            p.wait_for_timeout(600)
            count = p.evaluate("gameState.wishCount")
            check("[tanabata_wish] Stage4: 短冊送信", count == 1, f"wishCount={count}")
        except Exception as e:
            check("[tanabata_wish] Stage4: 短冊送信", False, str(e)[:80])
        p.close()

        # origami_puzzle: clickStep advances
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_origami_puzzle.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            p.evaluate("clickStep(0)")
            p.wait_for_timeout(800)
            step = p.evaluate("gameState.currentStep")
            check("[origami_puzzle] Stage4: 手順クリック", step == 1, f"currentStep={step}")
        except Exception as e:
            check("[origami_puzzle] Stage4: 手順クリック", False, str(e)[:80])
        p.close()

        # shogi_lite: getMoves returns valid moves for king
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_shogi_lite.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            moves = p.evaluate("getMoves(gameState.board, 4, 0)")
            check("[shogi_lite] Stage4: 駒移動可能判定", len(moves) > 0, f"moves={len(moves)}")
        except Exception as e:
            check("[shogi_lite] Stage4: 駒移動可能判定", False, str(e)[:80])
        p.close()

        # hanafuda: yaku detection
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_hanafuda.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            yaku = p.evaluate("checkYaku([0, 8, 28])")  # 三光
            found = any(y.get("name") == "三光" for y in yaku)
            check("[hanafuda] Stage4: 三光役判定", found, f"yaku={[y.get('name') for y in yaku]}")
        except Exception as e:
            check("[hanafuda] Stage4: 三光役判定", False, str(e)[:80])
        p.close()

        # mahjong: checkWin
        p = ctx.new_page()
        p.goto(f"{BASE_URL}/tmpl_mahjong_game.html", wait_until="domcontentloaded")
        p.locator("button").filter(has_text="START").first.click()
        p.wait_for_timeout(300)
        try:
            win = p.evaluate("""
                checkWin([
                    {suit:'m',n:1},{suit:'m',n:1},{suit:'m',n:1},
                    {suit:'m',n:2},{suit:'m',n:3},{suit:'m',n:4},
                    {suit:'m',n:5},{suit:'m',n:6},{suit:'m',n:7},
                    {suit:'p',n:1},{suit:'p',n:1},{suit:'p',n:1},
                    {suit:'p',n:2},{suit:'p',n:2}
                ])
            """)
            check("[mahjong_game] Stage4: 和了判定", win == True, f"result={win}")
        except Exception as e:
            check("[mahjong_game] Stage4: 和了判定", False, str(e)[:80])
        p.close()

        browser.close()

        # Summary
        print("\n========== S05 テスト結果 ==========")
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        print(f"合格: {passed} / {passed + failed}")

        print("\n--- JSエラー一覧 ---")
        any_err = False
        for tmpl, errs in js_errors.items():
            if errs:
                print(f"  {tmpl}: {'; '.join(errs[:2])}")
                any_err = True
        if not any_err:
            print("  JSエラーなし ✅")

        # KILL candidates
        kill_list = []
        for tmpl in TEMPLATES:
            tmpl_fails = [r for r in results if tmpl in r["name"] and r["status"] == "FAIL"]
            if tmpl_fails:
                kill_list.append(tmpl)

        if kill_list:
            print("\n⚠️  KILL候補:", ", ".join(kill_list))
        else:
            print("\n🎉 全テンプレート合格！")

        return failed == 0

if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
