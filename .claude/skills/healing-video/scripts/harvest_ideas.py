"""Idea generator for the "harvest-asmr" style (styles/harvest-asmr.md).

  python3 scripts/harvest_ideas.py next [--season summer] [--garden Korean] [--n 3]   # fresh idea as JSON
  python3 scripts/harvest_ideas.py list                                              # all ideas, used marked

An idea = a garden + one crop sequence (12 shots: wide opener, 10 harvest close-ups, basket + animal end).
No two ideas share a garden + crop sequence; `next` skips ideas used in ~/.config/museai/healing-history.json
(recorded with `ideas.py record custom --home <garden> --task <crops> --caption style:harvest-asmr ...`),
gardens used in the last 10 videos of ANY healing style, and the style of the last video (rotation).
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ideas as bank  # noqa: E402

STYLE = "harvest-asmr"
SOUND = {
    "snip": "the crisp snip of small pruning scissors",
    "pluck": "a soft dry snap of the stem and the rustle of leaves",
    "pull": "the soft tearing of fine roots out of damp soil",
    "twist": "a dry twist and a small pop as the stem lets go",
    "pick": "soft rustling leaves and the light patter of fruit dropping into a basket",
}
# garden: (region + season note, animal, [(crop, verb, plant and framing)] x 12+)
GARDENS = {
    "Korean countryside backyard": ("late summer", "cat", [
        ("cucumbers", "snip", "a long green cucumber hanging from a net trellis, yellow flower beside it"),
        ("red chili peppers", "pluck", "a chili plant heavy with red and green peppers"),
        ("perilla leaves", "pluck", "broad serrated perilla leaves in a raised row"),
        ("long purple eggplant", "snip", "a glossy long eggplant under big leaves"),
        ("green onions", "pull", "a row of green onions in dark soil, white roots coming up"),
        ("cherry tomatoes", "pick", "a truss of small red tomatoes on a bamboo stake"),
        ("zucchini", "snip", "a zucchini with a yellow flower among large prickly leaves"),
        ("yellow chamoe melons", "twist", "a small yellow-striped melon on the ground between vines"),
        ("jujube", "pick", "a jujube branch with red-brown fruit and small leaves"),
        ("kabocha pumpkin", "snip", "a dark green pumpkin with orange stem on a low vine"),
        ("garlic chives", "snip", "a dense clump of flat garlic chives with white flower buds"),
        ("sweet potato leaves", "pluck", "trailing heart-shaped sweet potato vines over the soil"),
    ]),
    "Provence kitchen garden": ("summer", "dog", [
        ("lavender", "snip", "a bush of purple lavender with bees on it"),
        ("apricots", "pick", "an apricot branch with orange-pink fruit"),
        ("basil", "pluck", "a thick clump of green basil in a terracotta-edged bed"),
        ("heirloom tomatoes", "twist", "a ribbed red-yellow tomato on the vine in strong sun"),
        ("figs", "twist", "a purple fig on a branch with big lobed leaves"),
        ("courgettes", "snip", "a striped courgette under spiky leaves"),
        ("thyme", "snip", "a low silvery-green thyme cushion between stones"),
        ("garlic", "pull", "a garlic bulb lifted from dry pale soil"),
        ("peaches", "twist", "a downy peach on a branch among narrow leaves"),
        ("rosemary", "snip", "a rosemary shrub with small blue flowers"),
        ("white grapes", "snip", "a bunch of translucent green grapes under vine leaves"),
        ("French beans", "pluck", "slim green beans hanging from bamboo poles"),
    ]),
    "Hokkaido farm garden": ("summer", "cat", [
        ("sweet corn", "twist", "a corn cob in a pale green husk on a tall stalk"),
        ("potatoes", "pull", "pale potatoes lifted from dark loamy soil with a fork beside"),
        ("blue honeysuckle berries", "pick", "a bush of dusty-blue oval berries"),
        ("edamame", "snip", "a plant covered in fuzzy green pods"),
        ("cherry tomatoes", "pick", "a yellow and red truss in a small plastic-covered tunnel"),
        ("pumpkin", "snip", "a grey-green pumpkin among broad leaves"),
        ("melon", "twist", "a netted orange melon lying on straw"),
        ("green peppers", "pluck", "bright green peppers on a compact plant"),
        ("onions", "pull", "a golden onion pulled from the ground, thin roots hanging"),
        ("strawberries", "pick", "red strawberries under leaves in a raised bed"),
        ("cucumber", "snip", "a cucumber with a withered yellow flower at its tip"),
        ("sunflower seeds", "snip", "a sunflower head bowed over with ripe seeds"),
    ]),
    "Tuscan hillside plot": ("autumn", "dog", [
        ("grapes", "snip", "a heavy bunch of dark grapes in a vineyard row"),
        ("olives", "pick", "an olive branch with green-black fruit"),
        ("figs", "twist", "a ripe split fig on a branch"),
        ("tomatoes", "twist", "a large red tomato on a staked plant"),
        ("sage", "snip", "grey-green sage leaves in the sun"),
        ("pomegranates", "snip", "a split red pomegranate on its branch"),
        ("peppers", "pluck", "yellow and red peppers on a bush"),
        ("artichokes", "snip", "a silvery artichoke head on a thick stalk"),
        ("walnuts", "pick", "green walnut husks on a branch"),
        ("kale", "pluck", "dark crinkled cavolo nero leaves in a row"),
        ("rosemary", "snip", "a rosemary hedge by a stone wall"),
        ("persimmons", "twist", "an orange persimmon on a bare branch"),
    ]),
    "Dutch allotment": ("late summer", "cat", [
        ("plums", "pick", "a branch of dusky blue plums among leaves"),
        ("runner beans", "pluck", "long green beans with red flowers on tall poles"),
        ("beetroot", "pull", "a round dark red beetroot lifted from soil"),
        ("sweet peas", "snip", "pink and white sweet peas on a wigwam"),
        ("courgettes", "snip", "a yellow courgette with a flower attached"),
        ("raspberries", "pick", "ripe raspberries among thorny stems"),
        ("carrots", "pull", "an orange carrot pulled from loose sandy soil"),
        ("apples", "twist", "a red-green apple on a low branch"),
        ("rhubarb", "pull", "pink rhubarb stalks under huge leaves"),
        ("dahlias", "snip", "a magenta dahlia on a tall stem"),
        ("kohlrabi", "snip", "a pale green kohlrabi in a bed"),
        ("blackcurrants", "pick", "glossy blackcurrants on a bush"),
    ]),
    "Vietnamese Da Lat greenhouse garden": ("dry season", "dog", [
        ("strawberries", "pick", "red strawberries hanging from a raised trough"),
        ("lettuce", "snip", "a frilly green lettuce head in a neat bed"),
        ("cherry tomatoes", "pick", "red tomatoes in a greenhouse with misty light"),
        ("artichoke flowers", "snip", "a purple-green artichoke bud on a tall stalk"),
        ("bok choy", "snip", "white-stemmed bok choy in a damp row"),
        ("rosemary", "snip", "a rosemary pot by the greenhouse door"),
        ("sweet peppers", "pluck", "red and yellow peppers in a polytunnel"),
        ("passion fruit", "twist", "a purple passion fruit on a trellis"),
        ("carrots", "pull", "a carrot with feathery leaves pulled from red soil"),
        ("hydrangeas", "snip", "a pale blue hydrangea bloom"),
        ("avocados", "twist", "a green avocado hanging on a tree"),
        ("herbs", "pluck", "mint and coriander in a bamboo planter"),
    ]),
    "Swedish summer cottage": ("summer", "cat", [
        ("wild strawberries", "pick", "tiny red strawberries in the grass under leaves"),
        ("peas", "pluck", "green pea pods on a string trellis"),
        ("new potatoes", "pull", "small yellow potatoes lifted from sandy soil"),
        ("dill", "snip", "tall feathery dill with yellow umbels"),
        ("lupins", "snip", "a tall purple lupin by a red wooden wall"),
        ("redcurrants", "pick", "strings of glossy redcurrants on a bush"),
        ("chives", "snip", "chives with round purple flowers"),
        ("gooseberries", "pick", "pale green striped gooseberries on a thorny bush"),
        ("radishes", "pull", "a pink radish pulled from the bed"),
        ("rhubarb", "pull", "red rhubarb stalks by a stone step"),
        ("blueberries", "pick", "blueberries on a low forest bush near the garden"),
        ("cornflowers", "snip", "blue cornflowers in a meadow strip"),
    ]),
    "Moroccan oasis garden": ("autumn", "cat", [
        ("pomegranates", "twist", "a red pomegranate among narrow leaves"),
        ("dates", "snip", "a hanging bunch of amber dates under palm fronds"),
        ("mint", "pluck", "dense green mint in a shaded irrigation channel bed"),
        ("figs", "twist", "a dark fig on a branch"),
        ("oranges", "twist", "a ripe orange in a glossy tree"),
        ("peppers", "pluck", "small red chillies on a dusty plant"),
        ("tomatoes", "twist", "red tomatoes on a staked vine in dry earth"),
        ("coriander", "snip", "bright green coriander in a narrow bed"),
        ("lemons", "twist", "a yellow lemon in a tree by a mud wall"),
        ("grapes", "snip", "green grapes under a pergola"),
        ("roses", "snip", "a pink damask rose on a thorny stem"),
        ("olives", "pick", "olive branches heavy with fruit"),
    ]),
    "Scottish Highlands polytunnel": ("summer", "dog", [
        ("raspberries", "pick", "red raspberries on canes in a tunnel"),
        ("kale", "pluck", "curly purple-green kale after rain"),
        ("tatties", "pull", "pale potatoes lifted with a fork from dark earth"),
        ("tomatoes", "twist", "a ripening truss inside a polytunnel"),
        ("gooseberries", "pick", "green gooseberries on a bush"),
        ("beans", "pluck", "purple climbing beans on poles"),
        ("mangetout", "pluck", "flat green pods on pea netting"),
        ("lettuce", "snip", "a red-green lettuce in a raised tray"),
        ("sweet peas", "snip", "a mix of pink and purple sweet peas"),
        ("carrots", "pull", "an orange carrot pulled from a deep bed"),
        ("strawberries", "pick", "ripe strawberries on a raised shelf"),
        ("marigolds", "snip", "orange marigolds beside the vegetable beds"),
    ]),
    "Kyoto machiya courtyard garden": ("autumn", "cat", [
        ("persimmons", "twist", "an orange kaki on a branch"),
        ("shiso", "pluck", "red-purple shiso leaves in a stone-edged planter"),
        ("ginger", "pull", "pink-tipped young ginger lifted from soil"),
        ("yuzu", "twist", "a yellow-green yuzu among thorny branches"),
        ("kabu turnips", "pull", "a white turnip pulled from the bed"),
        ("chrysanthemum", "snip", "a yellow chrysanthemum bloom in a clay pot"),
        ("green peppers", "pluck", "shishito peppers hanging on a small plant"),
        ("mizuna", "snip", "feathery mizuna leaves in a trough"),
        ("eggplant", "snip", "a round purple eggplant on a short bush"),
        ("chestnuts", "pick", "spiky chestnut burrs opened on the ground"),
        ("edamame", "snip", "a fuzzy edamame plant in a half barrel"),
        ("myoga", "pluck", "pale pink myoga buds at the base of a leafy clump"),
    ]),
    "Norwegian fjord farm garden": ("summer", "cat", [
        ("rhubarb", "pull", "thick red rhubarb stalks beside a wooden barn"),
        ("strawberries", "pick", "small sweet strawberries in a sunny bed"),
        ("redcurrants", "pick", "red currants on a bush by a white fence"),
        ("potatoes", "pull", "early potatoes lifted from light soil"),
        ("peas", "pluck", "green pea pods on a wire fence"),
        ("carrots", "pull", "thin orange carrots in a raised bed"),
        ("cherries", "pick", "dark red sour cherries on a branch"),
        ("lettuce", "snip", "a green lettuce head in a raised bed"),
        ("blackcurrants", "pick", "glossy black currants"),
        ("dill", "snip", "dill with yellow flowers by a wooden wall"),
        ("apples", "twist", "a small yellow-red apple on a low tree"),
        ("chives", "snip", "chives with purple blossoms by a stone step"),
    ]),
    "Welsh cottage vegetable plot": ("autumn", "dog", [
        ("pumpkins", "snip", "a big orange pumpkin on straw between vines"),
        ("apples", "twist", "a red apple on an old tree by a stone wall"),
        ("leeks", "pull", "a thick leek lifted from the soil with a fork"),
        ("blackberries", "pick", "black and red blackberries on a hedgerow bramble"),
        ("kale", "pluck", "dark curly kale in a row"),
        ("runner beans", "pluck", "long runner beans on a bean teepee"),
        ("pears", "twist", "a green-gold pear on a wall-trained tree"),
        ("carrots", "pull", "orange carrots from a raised bed"),
        ("beetroot", "pull", "a beetroot pulled out with leaves attached"),
        ("sunflowers", "snip", "a drooping sunflower head heavy with seeds"),
        ("damsons", "pick", "small purple damsons on a branch"),
        ("sweetcorn", "twist", "a corn cob in its husk"),
    ]),
}
OPEN = "Wide shot, the garden in clear daylight: she stands with her back to the camera, holding up one freshly picked {crop}, a wicker basket of the harvest on the grass and a {animal} sitting beside it. The camera is held still, only the leaves stir."
CLOSE = "Top-down, the wicker basket on the grass full of {crops} in bright natural colours, her hand adds one more; a {animal} sits beside the basket, calm, tail curling, watching. The camera is held still. Sound: a soft thud of fruit into the basket, birdsong."
MID = ("Close-up, handheld phone POV, her hand in a cream knit sleeve {verb_phrase} {plant}. Bright natural daylight on wet-looking leaves. "
       "The camera is held almost still; only the plant moves. Sound: {sound}.")
VERB = {"snip": "snips with small pruning scissors", "pluck": "plucks", "pull": "pulls up",
        "twist": "twists off", "pick": "picks"}


def build():
    ideas = []
    for g, (season, animal, crops) in GARDENS.items():
        for v in range(3):
            rng = random.Random(f"{g}-{v}")
            pick = rng.sample(crops, 10)
            seq = [c[0] for c in pick]
            opener = rng.choice([c for c in pick if c[1] != "pluck"])[0]
            shots = [OPEN.format(crop=opener, animal=animal)]
            for crop, verb, plant in pick:
                shots.append(MID.format(verb_phrase=VERB[verb], plant=plant, sound=SOUND[verb]))
            shots.append(CLOSE.format(crops=", ".join(seq[:4]), animal=animal))
            key = hashlib.sha1("|".join(seq).encode()).hexdigest()[:4]
            ideas.append({
                "id": f"ha-{len(ideas) + 1:04d}", "concept": STYLE, "title": f"{g}, {season} harvest ({', '.join(seq[:3])}...)",
                "home": g, "season": season, "task": f"harvest {'/'.join(seq[:4])} #{key}", "animal": animal,
                "caption": f"style:{STYLE}", "sound": "birdsong, leaves, pruning snips", "shots": shots, "crops": seq,
            })
    return ideas


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    n.add_argument("--season")
    n.add_argument("--garden")
    n.add_argument("--n", type=int, default=1)
    sub.add_parser("list")
    a = ap.parse_args()
    hist = bank.load(bank.HIST, [])
    ideas = build()
    used = {h.get("task") for h in hist}
    recent = {bank.norm(h["home"]) for h in hist[-10:]}
    if a.cmd == "list":
        for i in ideas:
            print(f"{i['id']} {'USED ' if i['task'] in used else '     '}{i['title']}")
        return
    last_style = hist[-1].get("caption") if hist else None
    if last_style == f"style:{STYLE}":
        print(f"warning: last video was already {STYLE}; rotate to another style first", file=sys.stderr)
    out = [i for i in ideas if i["task"] not in used and bank.norm(i["home"]) not in recent
           and (not a.season or a.season in i["season"]) and (not a.garden or bank.norm(a.garden) in bank.norm(i["home"]))]
    if not out:
        sys.exit("no fresh harvest idea; add gardens/crops to GARDENS")
    out = out[:a.n]
    print(json.dumps(out if a.n > 1 else out[0], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
