#!/usr/bin/env python3
"""S12の5本をindex.htmlに安全に追記するパッチスクリプト"""
import re

INDEX = "/Users/yuhata/claude-workspace/designium/games/playtest-site/index.html"

with open(INDEX, encoding="utf-8") as f:
    html = f.read()

changed = False

# 既に追加済みかチェック
if "tmpl_match3_meta.html" in html:
    print("match3_meta: 既に追加済みスキップ")
else:
    # solveセクションの最後のカードの後に追加
    # tmpl_card_battle or tmpl_puzzle_battle or tmpl_solitaire の後
    patterns = [
        'href="tmpl_card_battle.html"',
        'href="tmpl_puzzle_battle.html"',
        'href="tmpl_solitaire.html"',
    ]
    new_cards = '''    <a class="card gap" href="tmpl_match3_meta.html" target="_blank">MATCH3 META［テンプレ検証］</a>
    <a class="card gap" href="tmpl_board_game.html" target="_blank">REVERSI［テンプレ検証］</a>'''
    for pat in patterns:
        m = re.search(r'(' + re.escape(pat) + r'[^\n]*\n)', html)
        if m:
            html = html[:m.end()] + new_cards + "\n" + html[m.end():]
            print(f"match3_meta + board_game: {pat} の後に追加")
            changed = True
            break
    else:
        print("ERROR: solve最後のカードが見つかりません")

if "tmpl_rts.html" in html:
    print("rts: 既に追加済みスキップ")
else:
    patterns = [
        'href="tmpl_hero_shooter.html"',
        'href="tmpl_strategy_action.html"',
        'href="tmpl_tower_defense.html"',
        'href="tmpl_cooking_action.html"',
    ]
    new_cards = '''    <a class="card gap" href="tmpl_rts.html" target="_blank">RTS BATTLE［テンプレ検証］</a>
    <a class="card gap" href="tmpl_soulslike.html" target="_blank">SOULS LITE［テンプレ検証］</a>'''
    for pat in patterns:
        m = re.search(r'(' + re.escape(pat) + r'[^\n]*\n)', html)
        if m:
            html = html[:m.end()] + new_cards + "\n" + html[m.end():]
            print(f"rts + soulslike: {pat} の後に追加")
            changed = True
            break
    else:
        print("ERROR: beat最後のカードが見つかりません")

if "tmpl_battle_royale.html" in html:
    print("battle_royale: 既に追加済みスキップ")
else:
    patterns = [
        'href="tmpl_survival_exploration.html"',
        'href="tmpl_horror_strategy.html"',
        'href="tmpl_roguelite.html"',
        'href="tmpl_run_and_gun.html"',
    ]
    new_cards = '''    <a class="card gap" href="tmpl_battle_royale.html" target="_blank">BATTLE ROYALE［テンプレ検証］</a>'''
    for pat in patterns:
        m = re.search(r'(' + re.escape(pat) + r'[^\n]*\n)', html)
        if m:
            html = html[:m.end()] + new_cards + "\n" + html[m.end():]
            print(f"battle_royale: {pat} の後に追加")
            changed = True
            break
    else:
        print("ERROR: survive最後のカードが見つかりません")

# カウント更新: solveセクション
def update_count(html, section_comment, old_count, new_count):
    pattern = rf'({re.escape(section_comment)}.*?<span class="count">){old_count}本(</span>)'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        html = html[:m.start(2)] + new_count + "本" + html[m.end(2)-5:]
        # 上記は壊れるかもしれないので別の方法
    return html

# カウント更新: 数を直接数える
def count_cards_in_section(html, section_start, section_end):
    start = html.find(section_start)
    end = html.find(section_end, start)
    section = html[start:end]
    return len(re.findall(r'class="card', section))

if changed:
    # solve count
    n = count_cards_in_section(html, "<!-- solve -->", "<!-- beat -->")
    html = re.sub(
        r'(<!-- solve -->.*?<span class="count">)\d+本(</span>)',
        lambda m: m.group(1) + str(n) + "本" + m.group(2),
        html, count=1, flags=re.DOTALL
    )
    print(f"solve count → {n}本")

    # beat count
    n = count_cards_in_section(html, "<!-- beat -->", "<!-- survive -->")
    html = re.sub(
        r'(<!-- beat -->.*?<span class="count">)\d+本(</span>)',
        lambda m: m.group(1) + str(n) + "本" + m.group(2),
        html, count=1, flags=re.DOTALL
    )
    print(f"beat count → {n}本")

    # survive count
    n = count_cards_in_section(html, "<!-- survive -->", "<!-- feel -->")
    html = re.sub(
        r'(<!-- survive -->.*?<span class="count">)\d+本(</span>)',
        lambda m: m.group(1) + str(n) + "本" + m.group(2),
        html, count=1, flags=re.DOTALL
    )
    print(f"survive count → {n}本")

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html 更新完了")
else:
    print("変更なし")
