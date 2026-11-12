"""Build ../ideas-garden.json: the bank for the "garden montage" style (reference 5, "If a boring life
looks like this"): 10 one-second shots of an outdoor country life under one contrast caption.

  python3 scripts/gen_garden.py        # rewrites ideas-garden.json (deterministic)

Each idea = one real home x one season x one harvest, with 10 shot briefs built from the slots in SLOTS.
The hero shot (1) and the dusk shot (10) stay at the ends; slots 2-9 are shuffled per idea (seeded by
the idea number) so two videos never share the same running order. To widen the bank add homes, harvests
or captions at the END of the lists and rerun; ids stay stable because new rows are appended.
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ideas-garden.json"

# home: (house, land, animals, {season: (harvest crate/basket, food platter, flowers, meadow, dusk sky)})
HOMES = {
    "Lower Saxony brick farmhouse": (
        "a red-brick half-timbered farmhouse with green window frames and an old tiled roof",
        "flat green fields, big old oaks and hedgerows",
        ["cat", "hen"],
        {"summer": ("a wicker basket of dark plums, tomatoes, courgettes and beetroot", "a wooden board of melon, berries and orange slices laid on blue hydrangeas", "hydrangeas and dahlias", "a meadow of white clover and dandelion seed heads", "a pink and violet sunset behind oak trees"),
         "autumn": ("a wooden crate of apples, pumpkins and walnuts", "a board of sliced apples, grapes and figs on fallen leaves", "asters and sedum", "a meadow of long grass with the last clover", "an orange and pink sunset behind bare-topped oaks")}),
    "Cotswold stone cottage": (
        "a honey-coloured Cotswold stone cottage with a slate roof and roses round the door",
        "green sheep fields with dry-stone walls",
        ["cat", "sheepdog"],
        {"summer": ("a trug of sweet peas, strawberries, broad beans and new potatoes", "a plate of scones, jam and strawberries on a lawn among daisies", "roses and delphiniums", "a meadow of buttercups and ox-eye daisies", "a soft peach sunset over the dry-stone walls"),
         "spring": ("a trug of rhubarb, spring onions and radishes", "a plate of rhubarb crumble squares and a pot of tea among primroses", "tulips and blossom", "a meadow of cowslips and daisies", "a pale gold sunset over the hills")}),
    "Normandy half-timbered cottage": (
        "a brown-and-cream half-timbered Normandy cottage with a thatched roof and a blue door",
        "an apple orchard and cows beyond the hedge",
        ["cat", "cow"],
        {"autumn": ("a wooden crate of apples and quinces", "a board of apple slices, cheese and walnuts on straw", "chrysanthemums and cosmos", "an orchard meadow dotted with fallen apples", "a rose-gold sunset behind the apple trees"),
         "summer": ("a basket of cherries, peaches and fresh herbs", "a board of cherries and apricots on blue hydrangeas", "hydrangeas and hollyhocks", "a meadow of poppies and cornflowers", "an apricot sunset behind the apple trees")}),
    "Tyrol alpine farm": (
        "a dark-wood Tyrolean farmhouse with a stone-weighted roof and red geraniums on every balcony",
        "steep green hay meadows under grey peaks",
        ["cat", "goat"],
        {"summer": ("a basket of redcurrants, rhubarb and garden lettuce", "a board of bread, cheese and wild strawberries on a meadow", "red geraniums and gentians", "a steep meadow full of yellow hawkweed and bluebells", "pink light on the snow-streaked peaks"),
         "autumn": ("a crate of pumpkins, pears and plums", "a board of pear slices, cheese and walnuts on a bench", "dahlias and asters", "a hay meadow turning gold with cow bells in the distance", "a gold and rose sky behind the peaks")}),
    "Swedish red cottage": (
        "a falu-red Swedish cottage with white corners and a stone doorstep",
        "birch trees, a lake and wild meadows",
        ["cat", "dog"],
        {"summer": ("a wooden tray of new potatoes, dill, peas and strawberries", "a plate of strawberry cake on a table among lupins", "lupins and oxeye daisies", "a meadow of buttercups and red clover", "a long soft pink-orange midsummer sunset over the lake"),
         "autumn": ("a crate of lingonberries, chanterelles and apples", "a board of cinnamon buns and blueberries on a wooden jetty", "heather and rowan berries", "a field of golden grass at the forest edge", "a deep orange sunset through the birches")}),
    "Tuscan stone farmhouse": (
        "a sun-warmed stone Tuscan farmhouse with terracotta roof tiles and green shutters",
        "olive terraces, cypress lines and rolling hills",
        ["cat", "dog"],
        {"summer": ("a basket of tomatoes, basil, aubergines and figs", "a wooden board of figs, peaches and fresh cheese on a stone wall", "lavender and sunflowers", "a golden wheat field with red poppies", "an orange and violet sunset behind the cypress trees"),
         "autumn": ("a crate of grapes, olives and pumpkins", "a board of grapes, bread and pecorino on a vine-shaded table", "cyclamen and rosemary", "a vineyard slope in gold and rust", "a copper sunset behind the cypress trees")}),
    "Japanese satoyama farmhouse": (
        "a grey-tiled Japanese farmhouse with wooden verandas and a persimmon tree",
        "stepped rice paddies, bamboo and small mountains",
        ["cat", "hen"],
        {"autumn": ("a bamboo basket of persimmons, chestnuts, sweet potatoes and daikon", "a wooden tray of persimmon slices and rice dumplings on a veranda", "cosmos and red spider lilies", "a rice paddy ready for harvest, golden and gently moving", "a red-orange sunset behind the mountains"),
         "summer": ("a bamboo basket of cucumbers, tomatoes, green beans and shiso", "a tray of watermelon slices on a veranda with wind chimes", "hydrangeas and lotus", "a rice paddy of fresh bright green", "a pink and orange sunset over the paddies")}),
    "Vermont white farmhouse": (
        "a white clapboard New England farmhouse with a red barn and a stone wall",
        "maple woods, green pastures and old fences",
        ["cat", "dog"],
        {"autumn": ("a crate of apples, butternut squash and corn", "a board of apple slices, cheddar and maple cookies on a hay bale", "chrysanthemums and goldenrod", "a pasture edged with red and orange maples", "an orange and pink sunset behind the barn"),
         "summer": ("a basket of blueberries, sweet corn, tomatoes and zucchini", "a pie cut in slices with blueberries on a picnic table", "black-eyed Susans and phlox", "a hay field with the last light across it", "a pink sunset behind the red barn")}),
    "Provence mas": (
        "a pale stone Provencal mas with blue shutters and a plane tree in front",
        "lavender rows, vineyards and olive trees",
        ["cat", "dog"],
        {"summer": ("a basket of apricots, melons, tomatoes and lavender stems", "a board of apricots and goat cheese on a stone table by lavender", "lavender and sunflowers", "a lavender field in rows to the horizon", "a violet and orange sunset over the lavender rows"),
         "autumn": ("a crate of grapes, figs and pomegranates", "a board of figs, bread and honey on a sun-warmed wall", "rosemary and late roses", "a vineyard in russet and gold", "a red-orange sunset over the vineyard")}),
    "Bohemian village cottage": (
        "a whitewashed Czech village cottage with a tiled roof, wooden shutters and a plum tree",
        "orchards, rolling fields and a small pond",
        ["cat", "hen"],
        {"summer": ("a basket of raspberries, cucumbers, dill and early apples", "a board of raspberry buns and cherries on a garden table among sunflowers", "sunflowers and phlox", "a meadow of poppies and cornflowers", "a pink and gold sunset behind the plum trees"),
         "autumn": ("a wooden crate of plums, apples and pumpkins", "a board of plum dumplings and pears on straw", "asters and dahlias", "an orchard meadow in gold with falling leaves", "an orange sunset behind the orchard")}),
    "Irish stone cottage": (
        "a whitewashed Irish stone cottage with a red door and a slate roof",
        "emerald fields, stone walls and the sea beyond",
        ["cat", "sheepdog"],
        {"summer": ("a basket of potatoes, rhubarb, peas and spring onions", "a board of soda bread, butter and strawberries on a stone wall", "fuchsia and foxgloves", "a green field full of buttercups running down to the sea", "a long pink and gold sunset over the sea"),
         "autumn": ("a crate of apples, blackberries and kale", "a board of brown bread, butter and blackberries on a gate", "montbretia and heather", "a green field with sheep under a blue sky", "a red-gold sunset over the sea")}),
    "Polish wooden cottage": (
        "a log cottage with carved wooden eaves and a stork's nest on the barn",
        "wide meadows, birch lines and a slow river",
        ["cat", "dog"],
        {"summer": ("a basket of strawberries, dill, young potatoes and cucumbers", "a board of pierogi, berries and sour cream on a bench among mallows", "mallows and sunflowers", "a meadow of cornflowers and red clover", "an orange sunset behind the birches"),
         "autumn": ("a crate of apples, mushrooms and pumpkins", "a board of apple cake and plums on a garden table", "asters and rudbeckia", "a golden stubble field with a river bend", "a deep red sunset behind the birches")}),
    "Yunnan courtyard house": (
        "a grey-tiled Bai courtyard house with painted eaves and bougainvillea over the gate",
        "terraced fields, plum blossom hills and distant snow mountains",
        ["cat", "hen"],
        {"spring": ("a bamboo basket of fresh broad beans, spring greens and loquats", "a tray of flower cakes and plums on a courtyard table among camellias", "camellias and rapeseed flowers", "terraces of yellow rapeseed flowers rolling down the hill", "a pink and gold sunset behind the snow mountains"),
         "summer": ("a basket of wild mushrooms, peaches and green beans", "a tray of peaches and rice cakes on a courtyard table", "bougainvillea and roses", "a green terraced slope with a light breeze", "an orange sunset behind the mountains")}),
    "Hokkaido farm": (
        "a timber farmhouse with a steep red roof next to a tall silo",
        "huge rolling fields of lavender and potatoes under a wide sky",
        ["cat", "dog"],
        {"summer": ("a crate of sweet corn, melons, potatoes and tomatoes", "a board of melon slices and sweet corn on a picnic blanket", "lavender and sunflowers", "rolling patchwork fields in purple, green and gold", "an orange and purple sunset over the fields"),
         "autumn": ("a crate of pumpkins, potatoes and apples", "a board of baked sweet potatoes and apples on a hay bale", "cosmos and golden grass", "rolling fields of gold with straw rolls", "a deep red sunset over the fields")}),
    "Hungarian farmstead": (
        "a whitewashed farmhouse with a reed roof and a tall draw well",
        "the wide flat plain, sunflower fields and grazing horses",
        ["cat", "horse"],
        {"summer": ("a basket of peppers, tomatoes, apricots and corn", "a board of apricots, paprika bread and cheese on a wooden table", "sunflowers and mallows", "a sunflower field facing the sun", "a huge orange sunset over the plain"),
         "autumn": ("a crate of red peppers, grapes and walnuts", "a board of grapes, bread and walnuts on a wooden table", "asters and marigolds", "a golden stubble plain with horses", "a red sunset over the plain")}),
    "Slovenian hill farm": (
        "a white farmhouse with a red roof and a wooden hayrack beside it",
        "vineyard hills, hayracks and a church spire in the valley",
        ["cat", "dog"],
        {"summer": ("a basket of cherries, cucumbers, zucchini and lettuce", "a board of cherries and cheese on a hayrack bench", "geraniums and cornflowers", "a hay meadow with a wooden hayrack in the sun", "a pink sunset over the vineyard hills"),
         "autumn": ("a crate of grapes, pumpkins and chestnuts", "a board of grapes and honey cake on a wooden bench", "dahlias and chrysanthemums", "a vineyard slope in yellow and red", "an orange sunset over the valley")}),
}

ANIMAL = {  # animal: (wide beat, close beat)
    "cat": ("A cat walking slowly along a warm sunlit wall or roof edge", "Close-up of the same cat grooming a paw in the sun, soft fur"),
    "dog": ("A dog trotting along the sunny garden path", "Close-up of the same dog lying in the sun, panting softly, ears twitching"),
    "sheepdog": ("A sheepdog trotting along the sunny garden path", "Close-up of the same sheepdog lying in the grass, ears twitching"),
    "hen": ("A hen pecking her way across the sunny yard", "Close-up of the same hen scratching at the ground, feathers ruffled by the wind"),
    "goat": ("A goat grazing on the sunny slope beside the house", "Close-up of the same goat chewing, ears flicking, a bell clinking softly"),
    "cow": ("A cow grazing in the orchard beside the house", "Close-up of the same cow chewing slowly, tail flicking at a fly"),
    "horse": ("A horse grazing by the fence beside the house", "Close-up of the same horse's head, mane lifting in the wind, soft snort"),
}
# cat or dog etc. are the two animal beats; slot text uses {animal}
SLOTS = {
    "sky": "Blue sky with white clouds above {land}; the grass and leaves move in a light wind, a tiny bird or a distant farm vehicle far away. The camera is held still.",
    "basket": "Top-down view of {harvest} on sunlit grass among clover; the {animal} wanders into frame and sniffs at it, sunlight and leaf shadows over the food.",
    "path": "The garden path of {house}: a green arch of climbing plants over a gravel path, vegetable beds and {flowers} on both sides, leaves stirring in the breeze.",
    "platter": "Top-down view of {platter}, a slender young hand reaching in to straighten one piece, petals and leaves around it moving slightly in a light wind.",
    "animal1": "{a1} at {house}, bright leaves swaying in front of the lens.",
    "animal2": "{a2}, lit from the side, its small natural sounds clearly heard.",
    "meadow": "Walking-height view over {meadow}; the flowers and grass lean gently in the wind, trees at the far edge, a few insects drifting.",
    "window": "The wall of {house} with an open window and a jug of garden flowers on the sill, sun on the wall, leaves moving across the glass, the building itself perfectly still.",
}

CAPTIONS = [
    "If a boring life looks like this", "If a quiet life looks like this", "Tell me this isn't enough",
    "Imagine calling this ordinary", "A plain Tuesday, apparently", "Nobody told me slow could look like this",
    "In case you needed a reason to move to the country", "This is what I do on my days off",
    "If this is a quiet life, I'll take it", "A boring day in my life", "Just another ordinary day here",
    "Not much happens here, and I love it", "Imagine waking up to this", "Where I'd go if I could start again",
    "The kind of boring I want", "Please let my life look like this", "Slow living, apparently", "Life is not that complicated here",
]

OUTFITS = ["a red gingham cotton sundress with puff sleeves", "a pale blue linen pinafore dress over a white blouse",
           "a yellow cotton sundress with small white flowers", "a sage-green linen dress with rolled sleeves",
           "a white broderie-anglaise dress", "a faded pink striped cotton dress"]


def build():
    ideas, n = [], 0
    for home, (house, land, animals, seasons) in HOMES.items():
        for season, (harvest, platter, flowers, meadow, dusk) in seasons.items():
            n += 1
            rnd = random.Random(n)
            animal = animals[n % len(animals)]
            outfit = OUTFITS[n % len(OUTFITS)]
            ctx = dict(house=house, land=land, harvest=harvest, platter=platter, flowers=flowers, meadow=meadow,
                       animal=animal, a1=ANIMAL[animal][0], a2=ANIMAL[animal][1])
            mid = list(SLOTS)
            rnd.shuffle(mid)
            hero = (f"The young woman in {outfit}, seen from behind and the side, standing in the sunlit garden of {house}, "
                    f"holding up a freshly picked bunch from the beds; she snaps one stem off with a crisp sound as she picks; {flowers} around her, "
                    f"{land} behind, {season} sunshine.")
            shots = [hero] + [SLOTS[k].format(**ctx) for k in mid] + [f"{dusk.capitalize()} seen through trees above the roof of {house}; leaves move slightly, birds cross the sky, the camera is held still."]
            ideas.append({
                "id": f"gm-{n:04d}",
                "title": f"{season.capitalize()} garden montage: {home}",
                "home": home, "season": season, "task": harvest,
                "animal": animal, "caption": CAPTIONS[n % len(CAPTIONS)],
                "sound": "birdsong, a breeze in the leaves and soft small animal sounds",
                "outfit": outfit, "concept": "montage", "style": "garden", "shots": shots,
            })
    return ideas


if __name__ == "__main__":
    bank = build()
    OUT.write_text(json.dumps(bank, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(bank)} garden-montage ideas -> {OUT}")
