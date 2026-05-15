#!/usr/bin/env python3
"""S06 FB対応修正テスト: tmpl_rhythm.html / tmpl_runner_gate.html Stage4-CLEAR"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent.resolve()

def url(name):
    return f"file://{BASE}/{name}"

PASS = 0
FAIL = 0

def ok(name, msg=""):
    global PASS
    PASS += 1
    print(f"  PASS [{name}] {msg}")

def ng(name, msg=""):
    global FAIL
    FAIL += 1
    print(f"  FAIL [{name}] {msg}")


# ─────────────────────────────────────────────
# Rhythm — Stage4-CLEAR
# ─────────────────────────────────────────────

def test_rhythm(p):
    name = "リズム"
    print(f"\n[{name}] Stage4-CLEAR")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 480, "height": 700})
    page.goto(url("tmpl_rhythm.html"))

    # Stage1: start screen visible
    start_vis = page.evaluate("() => document.getElementById('startScreen').style.display")
    print(f"    startScreen={start_vis}")

    page.click("#startScreen button")
    page.wait_for_timeout(400)

    # Stage2: running
    running = page.evaluate("() => gameState.running")
    if not running:
        ng(name, "Stage2失敗: not running after start")
        page.close()
        return

    # Time-variable advance: pre-credit 29 notes as perfect (accuracy stays high).
    # 3 real notes will still spawn via setInterval (notesSpawned 29→32).
    page.evaluate("() => { gameState.notesSpawned = 29; gameState.perfect = 29; }")

    # Stage4: real key presses for the remaining 3 notes
    keys = ["d", "f", "j", "k"]
    for _ in range(16):
        for k in keys:
            page.keyboard.press(k)
        page.wait_for_timeout(80)

    # Wait for remaining notes to fall through auto-miss
    page.wait_for_timeout(2000)

    spawned = page.evaluate("() => gameState.notesSpawned")
    judged = page.evaluate("() => gameState.perfect + gameState.great + gameState.miss")
    remaining = page.evaluate("() => gameState.notes.filter(function(n){return !n.judged;}).length")
    print(f"    spawned={spawned} judged={judged} remaining={remaining}")

    clear_vis = page.evaluate("() => document.getElementById('clearScreen').style.display")
    if clear_vis == "flex":
        ok(name, f"Stage4-CLEAR: clearScreen表示 judged={judged}")
    else:
        state = page.evaluate("() => ({ running: gameState.running, notesSpawned: gameState.notesSpawned, perfect: gameState.perfect, great: gameState.great, miss: gameState.miss })")
        ng(name, f"clearScreen未表示 state={state}")
        page.close()
        return

    # RETRY
    page.click("#retryClearBtn")
    page.wait_for_timeout(300)
    start_vis2 = page.evaluate("() => document.getElementById('startScreen').style.display")
    if start_vis2 == "flex":
        ok(name, "RETRY → startScreen復帰")
    else:
        ng(name, f"RETRY失敗: startScreen={start_vis2}")

    page.close()


def test_rhythm_density(p):
    """ノート密度確認: 3秒で10本以上スポーンすること（250ms intervalの確認）"""
    name = "リズム密度"
    print(f"\n[{name}] 密度確認")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 480, "height": 700})
    page.goto(url("tmpl_rhythm.html"))

    page.click("#startScreen button")
    page.wait_for_timeout(3000)

    spawned = page.evaluate("() => gameState.notesSpawned")
    # 250ms interval × 3000ms = 12 expected (旧500ms=6)
    if spawned >= 10:
        ok(name, f"3秒で{spawned}ノート生成（250ms density確認）")
    else:
        ng(name, f"3秒で{spawned}ノートしか生成されていない（期待:10以上）")

    page.close()


# ─────────────────────────────────────────────
# Gate Runner — Stage4-CLEAR
# ─────────────────────────────────────────────

def test_runner_gate(p):
    name = "ゲートランナー"
    print(f"\n[{name}] Stage4-CLEAR")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 480, "height": 700})
    page.goto(url("tmpl_runner_gate.html"))

    page.click("#startScreen button")
    page.wait_for_timeout(400)

    # Stage2
    running = page.evaluate("() => gameState.running")
    if not running:
        ng(name, "Stage2失敗: not running")
        page.close()
        return

    # Time-variable advance: set passed=18, clear existing gates
    page.evaluate("""() => {
        gameState.passed = 18;
        gameState.gates = [];
        gameState.misses = 0;
        gameState.invincibleFrames = 0;
    }""")

    # Stage4: position runner via evaluate (time-var advance), hold key to keep in place,
    # inject gate just above hit zone and let it fall through.
    # Left opening: x=0..100 (runner center must be <100), right: x=300..400 (center >=300).
    for side, runner_x in [("left", 10), ("right", 350)]:
        key = "ArrowLeft" if side == "left" else "ArrowRight"
        page.evaluate(f"""() => {{
            gameState.runnerX = {runner_x};
            gameState.gates = [{{
                y: HIT_ZONE_TOP - 30,
                correctSide: '{side}',
                revealed: true,
                passed: false,
                missed: false,
                speed: 3,
                opening: 100,
                revealDist: 30
            }}];
        }}""")
        page.keyboard.down(key)  # real key press — keeps runner in opening while gate falls
        page.wait_for_timeout(700)  # gate travels from HIT_ZONE_TOP-30 through hit zone
        page.keyboard.up(key)
        page.wait_for_timeout(100)

    page.wait_for_timeout(500)

    final = page.evaluate("() => ({ passed: gameState.passed, misses: gameState.misses, running: gameState.running })")
    clear_vis = page.evaluate("() => document.getElementById('clearScreen').style.display")
    print(f"    passed={final['passed']} misses={final['misses']} clearScreen={clear_vis}")

    if clear_vis in ("flex", "block"):
        ok(name, f"Stage4-CLEAR: clearScreen表示 passed={final['passed']}")
    else:
        ng(name, f"clearScreen未表示 state={final}")
        page.close()
        return

    # RETRY
    page.click("#clearRetryBtn")
    page.wait_for_timeout(300)
    start_vis2 = page.evaluate("() => { const s = document.getElementById('startScreen'); return s ? s.style.display : 'missing'; }")
    if start_vis2 in ("flex", "block"):
        ok(name, "RETRY → startScreen復帰")
    else:
        ng(name, f"RETRY失敗: startScreen={start_vis2}")

    page.close()


def test_runner_gate_progression(p):
    """難易度進行確認: tier1以降でspeed/openingが変化すること"""
    name = "ゲートランナー難易度進行"
    print(f"\n[{name}] 進行確認")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 480, "height": 700})
    page.goto(url("tmpl_runner_gate.html"))

    page.click("#startScreen button")
    page.wait_for_timeout(200)

    # Tier0: passed=0
    page.evaluate("() => { gameState.passed = 0; gameState.gates = []; gameState.lastSpawnFrame = -999; }")
    page.wait_for_timeout(800)
    gate0 = page.evaluate("() => { const g = gameState.gates[0]; return g ? { speed: g.speed, opening: g.opening } : null; }")

    # Tier1: passed=5
    page.evaluate("() => { gameState.passed = 5; gameState.lastSpawnFrame = -999; }")
    page.wait_for_timeout(800)
    gate1 = page.evaluate("() => { const gates = gameState.gates; const g = gates[gates.length-1]; return g ? { speed: g.speed, opening: g.opening } : null; }")

    print(f"    tier0: {gate0}")
    print(f"    tier1: {gate1}")

    if gate0 and gate1:
        if gate1["speed"] > gate0["speed"] or gate1["opening"] < gate0["opening"]:
            ok(name, f"難易度進行確認: speed {gate0['speed']}→{gate1['speed']}, opening {gate0['opening']}→{gate1['opening']}")
        else:
            ng(name, f"難易度進行なし: speed/opening変化なし")
    else:
        ng(name, f"ゲートデータ取得失敗: gate0={gate0} gate1={gate1}")

    page.close()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== S06 FB修正テスト開始 ===")
    with sync_playwright() as p:
        print("\n--- tmpl_rhythm.html ---")
        test_rhythm(p)
        test_rhythm_density(p)

        print("\n--- tmpl_runner_gate.html ---")
        test_runner_gate(p)
        test_runner_gate_progression(p)

    print(f"\n=== 結果: PASS {PASS} / FAIL {FAIL} / TOTAL {PASS+FAIL} ===")
    sys.exit(0 if FAIL == 0 else 1)
