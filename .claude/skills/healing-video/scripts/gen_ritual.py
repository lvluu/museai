"""Build ../ideas-ritual.json: the bank for the "pov-ritual" style (reference 7, "POV : All you need is
flowers and a cup of tea", 9:16, 9.2 s, measured 2026-11-13): 12 quick shots that tell ONE small ritual in
order - gather outside, see the village, bring it in, make the second thing step by step, an animal
wanders in, the finished table - under a two-line "POV : All you need is / A and B" caption.

  python3 scripts/gen_ritual.py        # rewrites ideas-ritual.json (deterministic)

Each idea = one home x one ritual x one season. The order of the 12 shots is FIXED (it is a story, unlike
the shuffled garden montage). The girl wears one outfit, written into every shot that shows her, so she
stays the same person. To widen the bank add homes or rituals at the END of the dicts and rerun.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ideas-ritual.json"

# home: (village wide shot, the room inside, the door the animal comes through, animals)
HOMES = {
    "Cotswold village": (
        "a row of honey-coloured Cotswold stone cottages along a narrow stream with a wooden bench and a stone bridge, trees behind",
        "a bright cream dining room with a dark-wood dresser full of blue-and-white china, a table with a linen cloth and rattan chairs",
        "a half-open wooden stable door onto the garden", ["duck", "hen"]),
    "Normandy orchard village": (
        "half-timbered Normandy cottages with thatched roofs among apple orchards, a lane and a low hedge",
        "a whitewashed farmhouse kitchen with a pine dresser of cream jugs, a long oak table and rush-seat chairs",
        "a half-open blue farmhouse door onto the orchard", ["goose", "hen"]),
    "Provence hill village": (
        "pale stone houses with blue shutters stacked on a hillside, a plane tree and a small square below",
        "a cool stone-floored kitchen with a painted cupboard of yellow pottery, a wooden table and straw chairs",
        "an open blue door onto a sunny courtyard", ["cat", "hen"]),
    "Swedish lakeside hamlet": (
        "falu-red cottages with white corners by a still lake, birches and a small wooden jetty",
        "a white-panelled kitchen with a grey-painted cupboard of striped china, a scrubbed pine table and spindle chairs",
        "a half-open white door onto the meadow", ["duck", "cat"]),
    "Tyrol mountain village": (
        "dark-wood farmhouses with flower balconies on a green slope, a white church tower and grey peaks",
        "a wood-panelled room with a carved cupboard of painted plates, a corner bench and a heavy table",
        "an open wooden door onto the meadow", ["goat kid", "hen"]),
    "Vermont farm village": (
        "white clapboard houses and a red barn along a country road, maple woods and a white church steeple",
        "a sunny farmhouse kitchen with a white hutch of ironstone jugs, a farm table and ladder-back chairs",
        "an open screen door onto the porch", ["lamb", "dog"]),
    "Irish coast village": (
        "whitewashed stone cottages with coloured doors along a harbour road, green fields and the sea",
        "a whitewashed kitchen with a painted dresser of willow-pattern plates, a deal table and a settle",
        "a half-open red half-door onto the yard", ["duck", "lamb"]),
    "Bohemian village": (
        "whitewashed village houses with red tiled roofs round a green with a pond and a chapel",
        "a white kitchen with a green-painted cupboard of flowered china, a wooden table and simple chairs",
        "an open wooden door onto the yard", ["goose", "cat"]),
    "Kyoto countryside farmhouse": (
        "grey-tiled farmhouses among rice terraces and bamboo, a small stream and wooded hills",
        "a tatami room with sliding paper doors, a low wooden cabinet of ceramic cups and a low table",
        "an open sliding door onto the engawa", ["cat", "hen"]),
    "Tuscan hill farm": (
        "a stone farmhouse with a terracotta roof on a hill of olive trees and cypress lines",
        "a stone-floored kitchen with an old chestnut cupboard of white pottery, a long table and straw chairs",
        "an open wooden door onto the olive terrace", ["goose", "cat"]),
}

# ritual: (A, B, walk, {season: (source close-up, gathered in hands)}, set down, cupboard, vessel, drawer,
#          the B action, final table, sound)
RITUALS = {
    "flowers and tea": (
        "flowers", "a cup of tea",
        "walking slowly down the garden path in green rubber boots, a galvanised watering can swinging in one hand",
        {"spring": ("tulips and narcissus in the garden bed", "a flat wicker basket of cut tulips and narcissus"),
         "summer": ("tall yellow snapdragons and sweet peas", "a flat wicker basket of snapdragons and sweet peas"),
         "autumn": ("tall yellow snapdragons and rust dahlias in low sun", "a flat wicker basket of dahlias, snapdragons and dried grasses")},
        "puts the jar of fresh flowers in the middle of the table",
        "opens the glass door of the china cupboard", "lifts out a white china teapot",
        "pulls open a drawer of small tea tins in a wicker tray", "pours amber tea from the teapot into a blue-and-white cup on a saucer, steam rising",
        "the table laid with the flowers and cups; she stands at the far end sipping her tea",
        "birdsong, boots on the path, a cupboard door, tea pouring"),
    "apples and cinnamon": (
        "apples", "cinnamon",
        "walking under the orchard trees in brown leather boots, an empty wicker basket on her arm",
        {"autumn": ("red apples on a branch with dew, leaves moving", "a wicker basket full of red and yellow apples")},
        "sets the basket of apples on the table",
        "opens the pantry cupboard", "lifts out a cream mixing bowl",
        "pulls open a drawer of spice jars, cinnamon sticks tied with string", "slices an apple into a pie dish and dusts it with cinnamon",
        "an apple pie on the table beside the basket of apples; she cuts the first slice",
        "birdsong, apples thudding softly into the basket, a knife on a board"),
    "eggs and warm bread": (
        "fresh eggs", "warm bread",
        "walking across the yard to the hen house in green rubber boots, a wire egg basket in her hand",
        {"spring": ("brown eggs nestled in straw in the hen house, a hen beside them", "a wire basket of brown and speckled eggs"),
         "summer": ("brown eggs in straw in the sunny hen house", "a wire basket of brown and speckled eggs"),
         "autumn": ("brown eggs in straw, low sun through the hen house slats", "a wire basket of brown and speckled eggs")},
        "sets the egg basket on the table",
        "opens the bread bin", "lifts out a round crusty loaf",
        "pulls open a drawer of linen napkins and a bread knife", "cuts a thick slice from the loaf, crumbs falling on the board",
        "breakfast laid out: bread, butter, boiled eggs in cups; she sits down with a cup of coffee",
        "hens clucking, a hen house door, a knife through crust"),
    "herbs and soup": (
        "herbs", "a pot of soup",
        "walking along the vegetable beds in brown leather boots, a wooden trug in her hand",
        {"summer": ("rosemary, thyme and sage in the herb bed, bees moving", "a bundle of rosemary, thyme and sage tied with string"),
         "autumn": ("rosemary and sage beside pumpkins in the vegetable bed", "a trug of sage, rosemary and a small pumpkin")},
        "lays the herbs on the table",
        "opens the pot cupboard", "lifts out an enamel cooking pot",
        "pulls open a drawer of glass jars of lentils and dried beans", "stirs the soup in the pot on the stove, steam rising",
        "two bowls of soup on the table with bread and the herbs; she sits down",
        "birdsong, a garden gate, a wooden spoon in the pot"),
    "berries and jam": (
        "berries", "a jar of jam",
        "walking between the fruit bushes in white canvas shoes, an enamel bowl in her hand",
        {"summer": ("ripe raspberries and redcurrants on the bush", "an enamel bowl heaped with raspberries and redcurrants"),
         "autumn": ("blackberries ripening on the bramble hedge", "an enamel bowl of blackberries")},
        "sets the bowl of berries on the table",
        "opens the pantry cupboard", "lifts out a copper jam pan",
        "pulls open a drawer of empty glass jars and lids", "stirs the bubbling berry jam in the pan with a wooden spoon",
        "jars of jam on the table next to toast and the bowl of berries; she spreads jam on a slice",
        "birdsong, berries dropping into the bowl, jam bubbling"),
    "roses and lemonade": (
        "roses", "lemonade",
        "walking along the rose border in white canvas shoes, garden scissors in one hand",
        {"summer": ("pink climbing roses on a wall in full sun", "an armful of pink and cream garden roses"),
         "spring": ("early pink roses opening on the arch", "a few pink roses and peonies in her arms")},
        "puts the roses in a glass jug on the table",
        "opens the glass door of the cupboard", "lifts out a tall glass pitcher",
        "pulls open a drawer with lemons and a wooden squeezer", "pours cloudy lemonade over ice into a glass, a lemon slice turning",
        "the table set with roses and glasses of lemonade; she sits by the open window and drinks",
        "birdsong, scissors snipping, ice clinking"),
}

OUTFITS = [
    "a brown cable-knit cardigan over a brown gingham skirt with a white lace petticoat",
    "a cream fisherman sweater over a long sage-green linen skirt",
    "a rust corduroy pinafore over a cream blouse",
    "an oatmeal cardigan over a blue-and-white striped cotton dress",
    "a soft pink linen smock dress with a white apron",
    "a forest-green knit cardigan over a long floral cotton skirt",
]

ANIMAL = {  # animal: (at the door, walking in)
    "duck": ("a white duck stepping in over the threshold", "the same white duck waddling across the stone floor"),
    "goose": ("a white goose standing at the threshold, head tilted", "the same white goose walking slowly across the floor"),
    "hen": ("a brown hen hopping in over the threshold", "the same brown hen pecking across the floor"),
    "cat": ("a ginger cat walking in through the door", "the same ginger cat crossing the floor and rubbing against a chair leg"),
    "lamb": ("a small white lamb peeking in at the door", "the same lamb trotting a few steps across the floor"),
    "goat kid": ("a small brown goat kid peeking in at the door", "the same goat kid stepping across the floor, ears flicking"),
    "dog": ("a golden retriever nosing the door open", "the same dog padding across the floor, tail wagging"),
}


def shots(house, ritual, season, outfit, animal):
    village, room, door, _ = HOMES[house]
    a, b, walk, by_season, set_down, cupboard, vessel, drawer, action, final, _ = RITUALS[ritual]
    source, gathered = by_season[season]
    her = f"the young woman in {outfit}"
    at_door, walking_in = ANIMAL[animal]
    return [
        f"Low shot from waist down: {her} {walk}, {season} vegetable garden on both sides, warm low sunlight.",
        f"Close-up of {source}, soft breeze moving the stems, {season} sunlight from the side.",
        f"Close-up from the chest down: {her} holding {gathered} against her body, only her hands and clothes in frame.",
        f"Wide still view of {village}, {season} colours, low warm sun, clear blue sky, a soft breeze in the trees.",
        f"Inside {room}, bright daylight from the windows. {her[0].upper() + her[1:]}, seen from behind, {set_down}.",
        f"Close-up over her shoulder: her hand {cupboard}; china and jugs on the shelves, she wears {outfit}.",
        f"Close-up of her hands as she {vessel}, her sleeve in frame, china on the shelves behind.",
        f"Close-up from the side: she {drawer}, her braid falling forward, face hidden.",
        f"Close-up of her hand as she {action}, on the linen-covered table.",
        f"Wide view from inside {room} toward {door}: {at_door}, sunny garden behind.",
        f"Low view inside {room}: {walking_in}, natural speed, sunlight on the floor.",
        f"Wide view of {room}: {final}. {her[0].upper() + her[1:]}, seen from the side, face turned away.",
    ]


def build():
    ideas, n = [], 0
    for house, (_, _, _, animals) in HOMES.items():
        for ritual, spec in RITUALS.items():
            for season in spec[3]:
                n += 1
                animal = animals[n % len(animals)]
                outfit = OUTFITS[n % len(OUTFITS)]
                a, b = spec[0], spec[1]
                ideas.append({
                    "id": f"pr-{n:04d}",
                    "title": f"{season.capitalize()} POV ritual: {ritual}, {house}",
                    "home": house, "season": season, "task": ritual, "animal": animal,
                    "caption": f"POV : All you need is\n{a} and {b}",
                    "sound": spec[10], "outfit": outfit, "concept": "ritual", "style": "pov-ritual",
                    "shots": shots(house, ritual, season, outfit, animal),
                })
    return ideas


if __name__ == "__main__":
    bank = build()
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(bank)} pov-ritual ideas -> {OUT}")
