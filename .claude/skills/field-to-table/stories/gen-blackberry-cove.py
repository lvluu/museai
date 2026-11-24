import json
from pathlib import Path

STYLES = Path(__file__).resolve().parent.parent / "styles.json"
style = next(s for s in json.loads(STYLES.read_text()) if s["id"] == "cornish-sea")

E = ["ELLIE"]
light = {
    "morning": "Fresh bright morning in early autumn after a night of rain, clean washed daylight, broken white clouds moving over a blue sky, everything wet and shining.",
    "late morning": "Bright breezy late morning in early autumn, plain clear daylight, a few white clouds, the sea pale blue-grey.",
    "afternoon": "Afternoon in early autumn, plain bright daylight from the small sea-facing window falling across the worktop, not golden.",
    "dusk": "Early dusk in early autumn, soft pale blue daylight over the sea and one plain bulb on in the kitchen; everything clearly visible.",
}
outfits = {
    "walk": "a navy-and-cream striped Breton top under a faded indigo linen shirt, rolled cream canvas trousers, worn tan leather sandals",
    "kitchen": "the navy-and-cream striped Breton top with the sleeves pushed to the elbow, a plain unbleached cotton apron, rolled cream canvas trousers",
    "supper": "a chunky cream fisherman's wool jumper over the striped top, rolled cream canvas trousers",
}
places = {
    "cliff path": "a narrow earth cliff path above the sea in Cornwall: wet tangled bramble bushes heavy with blackberries along both sides, gorse and bracken going brown, a low slate stone hedge with sea pinks in its cracks, the grey-blue sea and a small shingle cove far below, a whitewashed cottage with a slate roof further along the path",
    "garden": "a small walled cottage garden on the cliff: low whitewashed walls with grey slate tops, a few raised beds of sea kale and rosemary, an old stone outdoor sink with a brass tap against the wall, wet flagstones, the sea beyond the wall",
    "kitchen": "a small plain whitewashed fisherman's cottage kitchen: thick white walls, a worn scrubbed pine table, a cream enamel range cooker, a white ceramic sink under a small deep-set window looking at the sea, a few plain stoneware jars on one shelf, a slate floor",
    "window": "the deep-set sea window of the cottage kitchen with a wide painted wooden sill and a cushion on it: the end of the pine table against the wall below it, the grey-blue sea and the headland outside",
}
refs = {
    "cliff path": {"kind": "place", "brief": "The cliff path empty, nobody on it: the narrow wet earth path between bramble bushes heavy with blackberries, the slate stone hedge, the sea and the small cove below, the whitewashed cottage further along. Clean bright morning light after rain."},
    "kitchen": {"kind": "place", "brief": "The kitchen empty, nobody in it, seen from the door: the scrubbed pine table, the cream enamel range, the white sink under the small sea window, white walls, slate floor. Plain bright daylight."},
    "garden": {"kind": "place", "brief": "The walled garden empty, nobody in it: the low whitewashed walls with slate tops, the raised beds of sea kale and rosemary, the old stone sink with a brass tap, wet flagstones, the sea beyond. Bright daylight."},
    "the colander": {"kind": "prop", "brief": "An old enamel colander, white with a thin navy rim and a few small chips, empty, standing on a scrubbed pine table. Plain daylight."},
    "Pip": {"kind": "prop", "brief": "Pip the cat sitting upright on a whitewashed stone wall, looking slightly to the side, full body in view, bright daylight."},
}
B = []


def c(ch, w, t, o, cast, shot, move, px=0.5, py=0.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, outfit=o, kind="clip", cast=cast, shot=shot, move=move, _p=(px, py), **kw))


def s(ch, w, t, shot, hold=3.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, kind="still", cast=[], shot=shot, hold=hold, **kw))


BERRIES = "uneven wild blackberries, most glossy black, some still red or green, a few soft and squashed, a bramble leaf or two among them"
COL = "the old chipped white enamel colander with the navy rim"

# i. the brambles
s(1, "cliff path", "morning", "Wide empty landscape of the cliff path after rain, no woman and no person anywhere: wet brambles along the path, the slate hedge, the grey-blue sea and the small cove far below, clouds moving.", 5.0, chapter=True)
c(1, "cliff path", "morning", "walk", [], "Wide empty view along the wet cliff path toward the sea, nobody anywhere, the brambles and bracken shining after rain.", "Only the bracken and the grass move in the sea wind; nothing else moves and no one walks in.", 0.5, 0.55)
c(1, "cliff path", "morning", "walk", E, "Ellie seen from behind, small in the frame, walking slowly along the narrow wet cliff path with the empty enamel colander on her hip, the sea far below.", "She walks slowly away along the path, her shirt and braid moving in the wind; the camera stays perfectly still.", 0.5, 0.55, props=["the colander"])
c(1, "cliff path", "morning", "walk", [], "Close-up of a bramble cane after rain: a cluster of glossy black and red blackberries with raindrops on them, wet leaves, the blurred sea behind.", "The cane bobs gently in the wind and one raindrop falls from a berry; the berries stay on the cane.")
c(1, "cliff path", "morning", "walk", [], "Close-up of her fingers in a faded indigo linen sleeve picking one ripe blackberry off the cane with a small tug, the red unripe ones left on it.", "She pulls the berry off with a small tug and the cane springs back; the other berries stay.", 0.5, 0.5)
c(1, "cliff path", "morning", "walk", [], f"Close-up of {COL} held against her hip: {BERRIES} in the bottom of it; her fingers drop in two more.", "Two berries drop in with a soft knock on the enamel; the colander stays still.", 0.5, 0.55, props=["the colander"])
c(1, "cliff path", "morning", "walk", [], "Close-up of her hand in an indigo linen sleeve reaching carefully into the thorny brambles; the cuff catches on a thorn and she frees it.", "Her sleeve catches on a thorn, she lifts it free slowly and picks the berry behind it.", 0.5, 0.5)
c(1, "cliff path", "morning", "walk", E, "Ellie seen from the side and a little behind, standing in the brambles at the edge of the path, head bowed, picking with both hands, the sea behind her.", "She picks slowly with both hands, the wind moving loose strands of her hair; the camera stays locked off.", 0.45, 0.5)
c(1, "cliff path", "morning", "walk", [], "Close-up of her open palm: three blackberries and purple juice stains on her fingertips, one berry squashed flat.", "She tips the berries slowly off her palm out of frame; the juice stains stay on her fingertips.")
c(1, "cliff path", "morning", "walk", [], "Close-up of Pip the cat sitting on the slate stone hedge beside the path, the sea behind him, his fur ruffled by the wind.", "Pip narrows his eyes against the wind and his fur ruffles; the hedge stays still.", props=["Pip"])
c(1, "cliff path", "morning", "walk", [], "Close-up of the sea pinks and wet grass in the cracks of the slate hedge, raindrops on them.", "Only the grass and the sea pinks shiver in the wind; nothing else moves.")
s(1, "cliff path", "morning", "Wide empty view down to the small shingle cove: grey-blue sea, white foam on the shingle, wet dark rocks, nobody anywhere.", 4.0)
c(1, "cliff path", "morning", "walk", [], "Wide empty view of the small shingle cove from the cliff, nobody anywhere: small waves washing in over the grey shingle.", "Only the waves move, washing slowly up the shingle and drawing back with a hiss; no one walks in.", 0.5, 0.6)
c(1, "cliff path", "morning", "walk", E, "Ellie seen from behind walking back along the cliff path toward the whitewashed cottage, the colander full of blackberries on her hip.", "She walks slowly toward the cottage; the brambles move in the wind; the camera stays locked off.", 0.5, 0.5, props=["the colander"])

# ii. the stone sink
s(2, "garden", "late morning", "Close-up of the old stone outdoor sink against the whitewashed garden wall, no person: the brass tap, wet flagstones, a rosemary bush beside it, the sea above the wall.", 5.0, chapter=True)
c(2, "garden", "late morning", "walk", [], "Close-up of the brass tap over the stone sink: her hand turns it and clear water runs out.", "Her hand turns the tap slowly and the water starts to run into the sink with a splash.")
c(2, "garden", "late morning", "walk", [], f"Close-up of {COL} under the running tap in the stone sink: {BERRIES}, the water rinsing over them.", "Water runs over the berries and drains through the holes; a leaf floats up.", 0.5, 0.55)
c(2, "garden", "late morning", "walk", [], "Close-up of her fingers with purple-stained tips picking a bramble leaf and a green berry out of the wet blackberries in the colander.", "She lifts the leaf out slowly and flicks it away; the berries stay in the colander.")
c(2, "garden", "late morning", "walk", [], f"Close-up of {COL} resting on the slate top of the garden wall, wet blackberries in it, water dripping from the holes, the sea behind.", "Water drips slowly from the colander onto the slate; nothing else moves.", 0.5, 0.5, props=["the colander"])
c(2, "garden", "late morning", "walk", E, "Ellie seen from behind at the stone sink, head bowed, shaking water off her hands, the walled garden and the sea in front of her.", "She shakes her hands slowly and dries them on her shirt; the camera stays still.", 0.5, 0.5)
c(2, "garden", "late morning", "walk", [], "Close-up of the rosemary and sea kale in the raised bed, wet, moving in the wind.", "Only the leaves move in the wind; nothing else moves and no one walks in.")

# iii. the jam
s(3, "kitchen", "afternoon", "Wide view of the plain whitewashed kitchen with nobody in it: the colander of blackberries on the scrubbed pine table, the cream enamel range, the small sea window.", 5.0, chapter=True)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a wide heavy steel pan on the cream enamel range: her hands tip the wet blackberries from the enamel colander into it.", "The berries tumble into the pan with a soft rattle; a few roll to the side.", 0.5, 0.55)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the steel pan of blackberries: her hand pours white sugar from a small stoneware jug over them.", "The sugar pours slowly over the berries in a thin white stream.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the pan on the range: blackberries and sugar beginning to melt into dark purple juice; her wooden spoon stirs slowly.", "The wooden spoon stirs slowly and the berries slump into the juice; a thin steam rises.", 0.5, 0.55)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the dark purple blackberry jam bubbling slowly in the steel pan, steam rising.", "Thick bubbles rise and pop slowly with a soft blup; the pan stays still.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a cold white saucer: her wooden spoon drops a little dark blackberry jam onto it and her fingertip pushes it; the jam wrinkles.", "Her fingertip pushes the jam slowly and its skin wrinkles; the saucer stays still.")
c(3, "kitchen", "afternoon", "kitchen", E, "Ellie seen from the side at the cream range, head bowed over the pan, stirring the jam with a wooden spoon, the small sea window beside her.", "She stirs slowly; steam rises past the window; the camera stays locked off.", 0.45, 0.5)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a wide jam funnel on a clean glass jar on the pine table: her ladle pours hot dark blackberry jam into it.", "The jam pours slowly through the funnel and the jar fills; steam rises.", 0.5, 0.5)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of three glass jars of dark blackberry jam on the pine table, uneven levels, one with a purple drip down the side; her hand screws a plain lid on one.", "She screws the lid on slowly; the jars stay where they are.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of Pip the cat lying in a patch of daylight on the slate floor by the range.", "Pip stretches one white paw slowly and settles again; nothing else moves.", props=["Pip"])
s(3, "kitchen", "afternoon", "Close-up of the small deep-set window: the grey-blue sea and the headland outside, one jar of jam on the sill with light through it, no person.")

# iv. the crumble
s(4, "kitchen", "afternoon", "Top-down close-up of the scrubbed pine table: a stoneware bowl of flour, a block of butter on its paper, a jar of oats and a few blackberries beside it.", 5.0, chapter=True)
c(4, "kitchen", "afternoon", "kitchen", [], "Top-down close-up of the stoneware bowl of flour with cubes of butter; her fingertips rub them together into crumbs.", "Her fingertips rub the butter into the flour slowly and crumbs fall back into the bowl.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the stoneware bowl of buttery crumbs: her hand scatters a handful of oats and brown sugar over them and mixes with her fingers.", "The oats fall in and her fingers toss them through the crumbs slowly.")
c(4, "kitchen", "afternoon", "kitchen", [], f"Close-up of a plain oval white enamel baking dish: her hand tips the rest of the raw blackberries in, {BERRIES}.", "The berries roll into the dish and settle unevenly; a few roll to the edge.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the white enamel dish of raw blackberries: her hand spoons dark blackberry jam from a jar over them.", "A spoon of jam drops slowly over the berries and slides between them.")
c(4, "kitchen", "afternoon", "kitchen", [], "Top-down close-up of the white enamel dish: her hand sprinkles the buttery oat crumble over the blackberries, purple juice showing at the edges.", "The crumbs fall slowly and cover the berries in an uneven layer.", 0.5, 0.5)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the open door of the cream enamel range oven: her hands in a folded tea towel slide the crumble dish onto the rack.", "She slides the dish in slowly and lets go; the oven door stays open.")
c(4, "kitchen", "afternoon", "kitchen", E, "Ellie seen from behind at the white sink under the small sea window, washing a stoneware bowl, the sea outside.", "She rinses the bowl slowly under the tap; the camera stays still.", 0.5, 0.45)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a small steel saucepan on the range: milk with a split vanilla pod heating, the first wisps of steam.", "The milk shivers and a wisp of steam rises; the pan stays still.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the small saucepan of thick pale yellow custard: her wooden spoon stirs it slowly.", "The spoon draws slowly through the custard and it folds back thick; steam rises.", 0.5, 0.55)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the range oven door opening: the blackberry crumble in the white enamel dish, golden on top, dark purple juice bubbling up at the edges.", "The juice bubbles slowly at the edges and steam rolls out; the dish stays still.", 0.5, 0.5)

# v. the window
s(5, "window", "dusk", "Wide view of the whitewashed cottage from the cliff path at early dusk: one small lit window, the sea pale blue, nobody outside.", 5.0, chapter=True)
c(5, "window", "dusk", "supper", [], "Close-up of the end of the pine table under the sea window: the hot blackberry crumble in the white enamel dish set down on a folded cloth by her hands in cream wool sleeves.", "She sets the dish down slowly and draws her hands back; steam rises.")
c(5, "window", "dusk", "supper", [], "Close-up of a big spoon breaking into the crumble crust in the enamel dish, purple juice welling up.", "The spoon breaks through slowly with a soft crunch and the juice wells up around it.")
c(5, "window", "dusk", "supper", [], "Top-down close-up of a plain white bowl of blackberry crumble: her hand pours thick pale custard from a small jug over it.", "The custard pours slowly over the crumble and runs into the purple juice.")
s(5, "window", "dusk", "Top-down view of the end of the pine table at dusk: the bowl of crumble and custard, the enamel dish, a jar of blackberry jam, a mug of tea, a spoon, nobody.", 5.0)
c(5, "window", "dusk", "supper", E, "Ellie seen from behind sitting on the deep window sill cushion with the bowl in her lap, the pale blue sea outside the window.", "She settles slowly with the bowl and pulls her jumper sleeves over her hands; the camera stays locked off.", 0.5, 0.45)
c(5, "window", "dusk", "supper", [], "Close-up of the bowl in her lap: her spoon lifts crumble with custard and purple juice.", "The spoon lifts slowly out of the bowl and out of frame; steam rises.")
c(5, "window", "dusk", "supper", [], "Close-up of Pip the cat curled on the end of the window sill cushion beside her knee, the dusk sea behind.", "Pip breathes slowly and his ear twitches once; nothing else moves.", props=["Pip"])
c(5, "window", "dusk", "supper", [], "Wide view through the small window over the sea at dusk, nobody outside, a faint light on the headland.", "Only the sea moves, the waves slow and far below; nothing else moves and no one walks in.", 0.5, 0.5)

beats = []
for b in B:
    px, py = b.pop("_p", (0.5, 0.5))
    if b["kind"] == "clip":
        b["cuts"] = [[0.3, 4.4], [4.9, 4.2, 1.28, px, py]]
    if not b["cast"]:
        b.pop("cast")
    beats.append(b)
beats[-1]["cuts"] = [[0.3, 4.6], [5.0, 4.8, 1.2, 0.5, 0.5]]


def find(word):
    return next(i for i, b in enumerate(beats, 1) if word in b["shot"])


story = {
    "story_id": "fc-0015", "slug": "blackberry-cove", "title": "the last blackberries",
    "eyebrow": "after a night of rain", "season": "early autumn", "xf": 0.4,
    "style": style["id"], "camera": style["camera"], "grade": style["grade"], "music_lufs": style["music_lufs"],
    "shake": 2, "max_slow": 1.12,
    "light": light, "outfits": outfits, "places": places, "refs": refs,
    "chapters": [
        {"n": 1, "title": "i.  the brambles", "sub": "after a night of rain"},
        {"n": 2, "title": "ii.  the stone sink", "sub": "cold water, purple fingers"},
        {"n": 3, "title": "iii.  the jam", "sub": "sugar and a cold saucer"},
        {"n": 4, "title": "iv.  the crumble", "sub": "butter, oats, the oven"},
        {"n": 5, "title": "v.  the window", "sub": "custard and the sea"}],
    "beats": beats,
}
story["teaser"] = {
    "text": "It rained all night. The brambles saved the best ones for this morning.", "text_secs": 5.5,
    "shots": [[find("picking one ripe blackberry"), 0.5, 2.8], [find("rinsing over them"), 0.6, 2.6],
              [find("bubbling slowly in the steel pan"), 0.8, 2.6], [find("jam wrinkles"), 0.8, 2.6],
              [find("walking slowly along the narrow wet cliff path"), 1.0, 2.8], [find("breaking into the crumble crust"), 1.0, 2.6],
              [find("Pip the cat sitting on the slate stone hedge"), 1.0, 2.4], [find("sitting on the deep window sill"), 2.0, 3.6]]}
story["short"] = {
    "text": "wild blackberries, from the cliff to the bowl",
    "shots": [[find("picking one ripe blackberry"), 0.5, 2.8, 0.5], [find("purple juice stains"), 0.6, 2.4, 0.5],
              [find("bubbling slowly in the steel pan"), 0.6, 2.4, 0.5], [find("sprinkles the buttery oat crumble"), 0.8, 2.4, 0.5],
              [find("pours thick pale custard"), 1.0, 2.4, 0.5], [find("sitting on the deep window sill"), 2.0, 3.0, 0.5]]}
Path("story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False) + "\n")
print(len(beats), "beats", sum(b["kind"] == "clip" for b in beats), "clips")
