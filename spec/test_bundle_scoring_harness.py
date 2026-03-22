from pathlib import Path

from bots.utils.tactical.annotate_possible_orders import annotate_possible_orders
from bots.utils.tactical.estimate_bundle_score import estimate_bundle_score
from bots.utils.tactical.select_best_order_bundle import select_best_order_bundle
from spec.bundle_scoring_harness import (
    list_saved_game_phases,
    load_bundle_search_inputs,
    load_game_at_phase,
    run_bundle_search_from_saved_game,
)


GAME_PATH = Path(__file__).resolve().parent / 'game_data' / '3x3a.json'
TARGET_PHASE = 'F1902M'

# helper fn
def get_location(possible_orders, name):
    return next((obj for obj in possible_orders if obj["location"] == name), None)


def test_list_saved_game_phases_includes_current_phase():
    phases = list_saved_game_phases(GAME_PATH)

    assert TARGET_PHASE in phases
    assert phases[-1] == TARGET_PHASE


def test_load_game_at_phase_materializes_target_phase():
    game = load_game_at_phase(GAME_PATH, TARGET_PHASE)

    assert game.get_current_phase() == TARGET_PHASE
    assert sorted(power.name for power in game.powers.values()) == ['AUSTRIA', 'FRANCE']


def test_load_bundle_search_inputs_builds_real_orders():
    inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')

    assert inputs.game.get_current_phase() == TARGET_PHASE
    assert inputs.power_name == 'AUSTRIA'
    assert inputs.orderable_locations
    assert inputs.possible_orders
    assert all('location' in entry and 'orders' in entry for entry in inputs.possible_orders)


def test_run_bundle_search_from_saved_game_returns_candidates():
    bundle = run_bundle_search_from_saved_game(GAME_PATH, TARGET_PHASE, 'AUSTRIA', beam_width=8)

    assert bundle['candidate_bundles']
    assert bundle['recommended_orders']
    assert bundle['resolved_orders']

def test_attack_and_support_orders_exist():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    possible_orders = search_inputs.possible_orders
    all_orders = set()
    for orders_dict in possible_orders:
        all_orders.update(orders_dict['orders'])
    abc = get_location(possible_orders, "ABC")
    acb = get_location(possible_orders, "ACB")
    attacking_order = "A ABC - ABB"
    supporting_order = "A ACB S A ABC - ABB"
    assert attacking_order in abc['orders']
    assert supporting_order in acb['orders']
    assert attacking_order in all_orders
    assert supporting_order in all_orders

    bundle = select_best_order_bundle(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
        beam_width=64,
        include_non_moves=True,
    )

    matching_candidates = [
        candidate
        for candidate in bundle['candidate_bundles']
        if attacking_order in candidate['intended_orders']
        and supporting_order in candidate['intended_orders']
    ]

    assert bundle['candidate_bundles']
    if matching_candidates:
        assert matching_candidates[0]['bundle_rank'] >= 1


def test_supported_attack_into_enemy_territory_scores_above_unsupported_attack():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    supported_orders = [
        'A ABC - ABB',
        'A ACB S A ABC - ABB',
        'A ACC H',
    ]
    unsupported_orders = [
        'A ABC - ABB',
        'A ACB H',
        'A ACC H',
    ]

    supported_score, supported_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=supported_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    unsupported_score, unsupported_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=unsupported_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )

    assert supported_score > unsupported_score
    assert supported_breakdown['supported_enemy_attack_bonus'] > 0
    assert unsupported_breakdown['unsupported_enemy_attack_penalty'] > 0


def test_support_order_metrics_distinguish_friendly_from_enemy_support():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    friendly_support = annotation_by_order['A ACB S A ABC - ABB']['metrics']
    enemy_support = annotation_by_order['A ACB S A AAB - ABB']['metrics']

    assert friendly_support['supported_unit_power'] == 'AUSTRIA'
    assert friendly_support['supports_friendly_move'] == 1
    assert friendly_support['supports_enemy_move'] == 0

    assert enemy_support['supported_unit_power'] == 'FRANCE'
    assert enemy_support['supports_friendly_move'] == 0
    assert enemy_support['supports_enemy_move'] == 1
    assert enemy_support['net_score'] < friendly_support['net_score']


def test_enemy_support_bundle_scores_below_friendly_supported_attack_bundle():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    friendly_supported_orders = [
        'A ABC - ABB',
        'A ACB S A ABC - ABB',
        'A ACC H',
    ]
    enemy_support_orders = [
        'A ABC S A AAB - ABB',
        'A ACB S A AAB - ABB',
        'A ACC H',
    ]

    friendly_score, friendly_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=friendly_supported_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    enemy_score, enemy_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=enemy_support_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )

    assert friendly_score > enemy_score
    assert enemy_breakdown['supports_enemy_move_penalty'] > 0


def test_bundle_search_no_longer_recommends_supporting_the_enemy():
    bundle = run_bundle_search_from_saved_game(GAME_PATH, TARGET_PHASE, 'AUSTRIA', beam_width=64)

    assert 'A ABC S A AAB - ABB' not in bundle['recommended_orders']
    assert 'A ACB S A AAB - ABB' not in bundle['recommended_orders']


def test_dangling_friendly_support_bundle_is_penalized():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    dangling_support_orders = [
        'A ABC S A ACB - ABB',
        'A ACB S A ABC - ABB',
        'A ACC S A ABC - ACB',
    ]
    direct_attack_orders = [
        'A ABC - ABB',
        'A ACB S A ABC - ABB',
        'A ACC H',
    ]

    dangling_score, dangling_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=dangling_support_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    assert dangling_breakdown['dangling_support_penalty'] > 0
    assert dangling_score < 0


def test_bundle_search_no_longer_recommends_dangling_supports():
    bundle = run_bundle_search_from_saved_game(GAME_PATH, TARGET_PHASE, 'AUSTRIA', beam_width=64)
    recommended_orders = bundle['recommended_orders']

    recommended_order_set = {order.upper() for order in recommended_orders}
    for order in recommended_orders:
        supported_order = order.split(' S ', 1)[1] if ' S ' in order else None
        if supported_order and ' - ' in supported_order:
            assert supported_order.upper() in recommended_order_set

def test_move_into_already_held_territory():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    worse_move = ['A AAC H', 'A ABC - ACC', 'A ACB H', 'A ACC H']
    better_move = ['A ABC - ABB', 'A ACB S A ABC - ABB', 'A AAC S A ABC - ABB']

    better_move_score, better_move_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=better_move,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    worse_move_score, worse_move_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=worse_move,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    assert better_move_score > worse_move_score

def test_hand_crafted_move_vs_bundle_search():
    search_inputs = load_bundle_search_inputs(GAME_PATH, TARGET_PHASE, 'AUSTRIA')
    annotations = annotate_possible_orders(
        power_name=search_inputs.power_name,
        possible_orders=search_inputs.possible_orders,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
    )
    annotation_by_order = {str(entry['order']): entry for entry in annotations}

    best_bundle = run_bundle_search_from_saved_game(GAME_PATH, TARGET_PHASE, 'AUSTRIA', beam_width=64)
    bundle_search_orders = best_bundle['recommended_orders']

    hand_crafted_move = ['A ABC - ABB', 'A ACB S A ABC - ABB', 'A AAC S A ABC - ABB']

    bundle_move_score, bundle_move_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=bundle_search_orders,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    hand_crafted_move_score, hand_crafted_move_breakdown, _ = estimate_bundle_score(
        power_name=search_inputs.power_name,
        orders=hand_crafted_move,
        annotation_by_order=annotation_by_order,
        units_by_power=search_inputs.units_by_power,
        centers_by_power=search_inputs.centers_by_power,
        loc_abut=search_inputs.loc_abut,
        supply_centers=search_inputs.supply_centers,
    )
    assert bundle_move_score > hand_crafted_move_score
