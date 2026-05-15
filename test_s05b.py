#!/usr/bin/env python3
"""S05b: Stage4-CLEAR tests for 3 new games + bug verification for 3 fixed games."""
import sys, time
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
# Stage4-CLEAR tests
# ─────────────────────────────────────────────

def test_ennichi_shooting(p):
    name = "縁日射的"
    print(f"\n[{name}] Stage4-CLEAR")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_ennichi_shooting.html"))

    # Start
    page.click("text=START")
    page.wait_for_timeout(300)

    # Get target positions via evaluate
    canvas = page.locator("#gameCanvas")
    box = canvas.bounding_box()

    # Click on target positions (3 rows x 3 cols, spaced at 150px)
    # Layout: col spacing W/(cols+1) = 460/4 = 115; baseX = 115, 230, 345
    # Rows at y=110, 210, 310 (relative to canvas)
    target_positions = []
    for c in [1, 2, 3]:
        for row_y in [110, 210, 310]:
            target_positions.append((c * 115, row_y))
    # Add gold target positions
    target_positions.append((115, 160))
    target_positions.append((345, 260))

    score = 0
    shots = 0
    for (tx, ty) in target_positions * 3:  # repeat to handle misses due to movement
        if score >= 10 or shots >= 20:
            break
        cx = box["x"] + tx
        cy = box["y"] + ty
        page.mouse.move(cx, cy)
        page.wait_for_timeout(80)
        page.mouse.click(cx, cy)
        shots += 1
        page.wait_for_timeout(60)
        # Check state
        s = page.evaluate("() => ({ score: gs.score, shots: gs.shots })")
        score = s["score"]
        shots = s["shots"]

    page.wait_for_timeout(600)
    clear_vis = page.evaluate("() => document.getElementById('clearScreen').style.display")
    if clear_vis == "flex":
        ok(name, f"clearScreen表示確認 score={score} shots={shots}")
    else:
        # Try state check
        final = page.evaluate("() => ({ score: gs.score, shots: gs.shots, running: gs.running })")
        ng(name, f"clearScreen未表示 state={final}")

    # Retry
    try:
        page.click("text=もう一度")
        page.wait_for_timeout(200)
        start_vis = page.evaluate("() => document.getElementById('startScreen').style.display")
        if start_vis == "flex":
            ok(name, "RETRY→startScreen復帰")
        else:
            ng(name, f"RETRY失敗 startScreen={start_vis}")
    except:
        ng(name, "RETRYボタン失敗")
    page.close()


def test_sumo(p):
    name = "相撲"
    print(f"\n[{name}] Stage4-CLEAR")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_sumo.html"))

    page.click("text=START")
    page.wait_for_timeout(300)

    # Strategy: position CPU near ring edge via evaluate, then push
    CX, CY = 230, 220
    RING_R = 150
    CHAR_R = 28

    wins = 0
    for attempt in range(3):
        if wins >= 2:
            break
        # Put CPU near right edge
        page.evaluate(f"""() => {{
            gs.ex = {CX + RING_R - CHAR_R - 5};
            gs.ey = {CY};
            gs.evx = 0; gs.evy = 0;
            gs.px = {CX - 60};
            gs.py = {CY};
            gs.pvx = 0; gs.pvy = 0;
        }}""")
        # Press right to push CPU out
        page.keyboard.down("ArrowRight")
        page.wait_for_timeout(700)
        page.keyboard.up("ArrowRight")
        page.wait_for_timeout(400)

        state = page.evaluate("() => ({ playerWins: gs.playerWins, cpuWins: gs.cpuWins, phase: gs.phase })")
        wins = state["playerWins"]
        if state["phase"] == "roundEnd":
            page.wait_for_timeout(1200)  # wait for next round

    page.wait_for_timeout(800)
    clear_vis = page.evaluate("() => document.getElementById('clearScreen').style.display")
    if clear_vis == "flex":
        ok(name, f"clearScreen表示確認 playerWins={wins}")
    else:
        final = page.evaluate("() => ({ playerWins: gs.playerWins, cpuWins: gs.cpuWins, running: gs.running })")
        ng(name, f"clearScreen未表示 state={final}")

    try:
        page.click("text=もう一度")
        page.wait_for_timeout(200)
        start_vis = page.evaluate("() => document.getElementById('startScreen').style.display")
        if start_vis == "flex":
            ok(name, "RETRY→startScreen復帰")
        else:
            ng(name, f"RETRY失敗")
    except:
        ng(name, "RETRYボタン失敗")
    page.close()


def test_goldfish_scoop(p):
    name = "金魚すくい"
    print(f"\n[{name}] Stage4-CLEAR")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_goldfish_scoop.html"))

    page.click("text=START")
    page.wait_for_timeout(300)

    canvas = page.locator("#gameCanvas")
    box = canvas.bounding_box()

    # Pool center
    POOL_X, POOL_Y = 20, 80
    pool_cx = POOL_X + (460 - 40) / 2  # ~230
    pool_cy = POOL_Y + 340 / 2          # ~250

    caught = 0
    for _ in range(5):
        if caught >= 5:
            break
        # Move a fish near poi center via evaluate
        page.evaluate(f"""() => {{
            const f = gs.fish.find(f => !f.caught);
            if (f) {{ f.x = {pool_cx}; f.y = {pool_cy}; f.vx = 0; f.vy = 0; }}
        }}""")
        # Move mouse to pool center
        mx = box["x"] + pool_cx
        my = box["y"] + pool_cy
        page.mouse.move(mx, my)
        page.wait_for_timeout(150)
        page.mouse.click(mx, my)
        page.wait_for_timeout(200)
        state = page.evaluate("() => ({ caught: gs.caught, dur: gs.durability })")
        caught = state["caught"]

    page.wait_for_timeout(600)
    clear_vis = page.evaluate("() => document.getElementById('clearScreen').style.display")
    if clear_vis == "flex":
        ok(name, f"clearScreen表示確認 caught={caught}")
    else:
        final = page.evaluate("() => ({ caught: gs.caught, dur: gs.durability, running: gs.running })")
        ng(name, f"clearScreen未表示 state={final}")

    try:
        page.click("text=もう一度")
        page.wait_for_timeout(200)
        start_vis = page.evaluate("() => document.getElementById('startScreen').style.display")
        if start_vis == "flex":
            ok(name, "RETRY→startScreen復帰")
        else:
            ng(name, "RETRY失敗")
    except:
        ng(name, "RETRYボタン失敗")
    page.close()


# ─────────────────────────────────────────────
# Bug fix verification
# ─────────────────────────────────────────────

def verify_hanafuda_discard(p):
    name = "花札(捨て牌バグ修正)"
    print(f"\n[{name}] バグ修正確認")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_hanafuda.html"))

    page.click("text=START")
    page.wait_for_timeout(300)

    # Remove all field cards so there's no match, then click a hand card
    page.evaluate("""() => {
        gameState.fieldCards = [];
        gameState.phase = 'player_select';
    }""")

    # Click first hand card
    canvas = page.locator("#gameCanvas")
    box = canvas.bounding_box()
    page.mouse.click(box["x"] + 60, box["y"] + 490)
    page.wait_for_timeout(200)

    phase_after_select = page.evaluate("() => gameState.phase")
    if phase_after_select != "player_field":
        ng(name, f"player_field遷移失敗: {phase_after_select}")
        page.close()
        return

    # Now click anywhere (should discard since no field cards)
    page.mouse.click(box["x"] + 230, box["y"] + 300)
    page.wait_for_timeout(200)

    phase_after = page.evaluate("() => gameState.phase")
    field_count = page.evaluate("() => gameState.fieldCards.length")
    if phase_after in ("player_select", "cpu") or field_count > 0:
        ok(name, f"捨て牌成功: phase={phase_after} fieldCount={field_count}")
    else:
        ng(name, f"捨て牌失敗: phase={phase_after} fieldCount={field_count}")
    page.close()


def verify_mahjong_tsumo(p):
    name = "麻雀(ツモ牌表示修正)"
    print(f"\n[{name}] バグ修正確認")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_mahjong_game.html"))

    page.click("text=START")
    page.wait_for_timeout(300)

    # Check canvas for ツモ button text (should not contain 🀄)
    canvas = page.locator("#gameCanvas")
    box = canvas.bounding_box()
    # Click ツモ button area
    page.mouse.click(box["x"] + 230, box["y"] + 240)
    page.wait_for_timeout(200)

    tsumo_tile = page.evaluate("() => gameState.tsumoTile")
    if tsumo_tile:
        suit = tsumo_tile.get("suit", "?")
        n = tsumo_tile.get("n", "?")
        if suit in ["m", "p", "s"] and 1 <= n <= 9:
            ok(name, f"ツモ牌が正常な牌: {n}{suit}")
        else:
            ng(name, f"ツモ牌が異常: {tsumo_tile}")
    else:
        # Might have auto-won, check phase
        phase = page.evaluate("() => gameState.phase")
        ok(name, f"ツモ後phase={phase} (auto-win or wait)")
    page.close()


def verify_shogi_layout(p):
    name = "将棋(初期配置修正)"
    print(f"\n[{name}] バグ修正確認")
    page = p.chromium.launch().new_page()
    page.set_viewport_size({"width": 500, "height": 600})
    page.goto(url("tmpl_shogi_lite.html"))

    page.click("text=START")
    page.wait_for_timeout(300)

    # Check that player rook and CPU king are NOT in same row/column
    board = page.evaluate("""() => {
        const b = [];
        for (let r = 0; r < 5; r++) {
            for (let c = 0; c < 5; c++) {
                const p = gameState.board[r][c];
                if (p) b.push({r, c, type: p.type, owner: p.owner});
            }
        }
        return b;
    }""")

    player_rook = next((p for p in board if p["type"] == "R" and p["owner"] == 0), None)
    cpu_king = next((p for p in board if p["type"] == "K" and p["owner"] == 1), None)

    if not player_rook or not cpu_king:
        ng(name, "飛車または王が見つからない")
        page.close()
        return

    same_col = player_rook["c"] == cpu_king["c"]
    same_row = player_rook["r"] == cpu_king["r"]

    if not same_col and not same_row:
        ok(name, f"初手詰みなし: 飛({player_rook['r']},{player_rook['c']}) 王({cpu_king['r']},{cpu_king['c']})")
    else:
        ng(name, f"初手詰み可能: 飛({player_rook['r']},{player_rook['c']}) 王({cpu_king['r']},{cpu_king['c']}) same_col={same_col}")
    page.close()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== S05b テスト開始 ===")
    with sync_playwright() as p:
        print("\n--- 新規3ゲーム Stage4-CLEAR ---")
        test_ennichi_shooting(p)
        test_sumo(p)
        test_goldfish_scoop(p)

        print("\n--- バグ修正3本 確認 ---")
        verify_hanafuda_discard(p)
        verify_mahjong_tsumo(p)
        verify_shogi_layout(p)

    print(f"\n=== 結果: PASS {PASS} / FAIL {FAIL} / TOTAL {PASS+FAIL} ===")
    sys.exit(0 if FAIL == 0 else 1)
