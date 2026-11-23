import json
from pathlib import Path

STYLES = Path(__file__).resolve().parent.parent / "styles.json"
style = next(s for s in json.loads(STYLES.read_text()) if s["id"] == "eastern-strings")

E = ["ELLIE"]
light = {
    "morning": "Early morning in late autumn, soft cool grey daylight, low white mist lying in the valley below the terraces.",
    "late morning": "Late morning in late autumn, bright soft overcast daylight, the mist lifting off the hills.",
    "afternoon": "Afternoon in late autumn, soft clear daylight from the open lattice window, bright, not golden.",
    "dusk": "Dusk in late autumn, soft blue fading daylight over the valley and one plain warm bulb on under the eaves; everything clearly visible.",
}
outfits = {
    "walk": "a loose undyed linen jacket with wide sleeves tied at the waist, wide flax-grey trousers, dark cloth shoes",
    "kitchen": "the undyed linen jacket with the wide sleeves rolled to the forearm, a dark-indigo linen apron, wide flax-grey trousers",
    "supper": "a soft oatmeal wool cardigan over the undyed linen jacket, wide flax-grey trousers",
}
places = {
    "terraces": "a terraced hillside kitchen garden above a misty green valley: narrow earth terraces held up by old mossy dry-stone walls, pumpkin vines with big rough leaves sprawling over a low bamboo trellis, rows of greens and spring onions, a bamboo grove at the top of the slope, a small timber-and-plaster house with a grey tiled roof and deep eaves",
    "spring": "a spring-fed stone basin beside the garden path under the bamboo grove: clear water running from a split bamboo pipe into a mossy carved stone trough, ferns around it, wet flat stepping stones",
    "kitchen": "a small plain timber kitchen with lime-plastered walls: a clay-brick stove with a wide black iron pan set into it and a wood fire under it, a heavy worn wooden worktop, a wide wooden lattice window open onto the valley, a few woven bamboo baskets and plain stoneware jars on one shelf",
    "porch": "a wooden porch at the front of the small house under the deep tiled eaves, a low worn wooden table and two low stools, the terraces and the misty valley below, a plain paper lamp hanging from the eave",
}
refs = {
    "terraces": {"kind": "place", "brief": "The terraced garden empty, nobody in it, seen from the top terrace: the dry-stone walls stepping down, the pumpkin vines over the bamboo trellis, the greens, the misty valley beyond, the corner of the small house. Soft grey morning light."},
    "kitchen": {"kind": "place", "brief": "The kitchen empty, nobody in it, seen from the doorway: the clay-brick stove with the wide black iron pan, the worn wooden worktop, the lattice window open onto the valley. Bright soft daylight."},
    "porch": {"kind": "place", "brief": "The porch empty, nobody on it: the low wooden table and two stools under the deep eaves, the terraces and the misty valley below. Soft daylight."},
    "the basket": {"kind": "prop", "brief": "A shallow round woven bamboo basket with a bent bamboo handle, empty, standing on a worn wooden worktop. Soft daylight."},
    "Pip": {"kind": "prop", "brief": "Pip the cat sitting upright on worn wooden floorboards, looking slightly to the side, full body in view, soft daylight."},
}
B = []


def c(ch, w, t, o, cast, shot, move, px=0.5, py=0.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, outfit=o, kind="clip", cast=cast, shot=shot, move=move, _p=(px, py), **kw))


def s(ch, w, t, shot, hold=3.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, kind="still", cast=[], shot=shot, hold=hold, **kw))


PUMPKIN = "a squat ribbed dusty-orange pumpkin with pale-green streaks and a dry curled stalk"

# i. the terraces
s(1, "terraces", "morning", "Wide empty landscape of the terraced hillside in the early mist, no woman and no person anywhere: dry-stone terraces stepping down into a white sea of mist, the bamboo grove dark at the top.", 5.0, chapter=True)
c(1, "terraces", "morning", "walk", [], "Wide empty view down the terraces into the misty valley, nobody anywhere.", "Only the mist moves, drifting slowly along the valley below; nothing else moves and no one walks in.", 0.5, 0.55)
c(1, "terraces", "morning", "walk", E, "Ellie seen from behind, small in the frame, walking slowly down the narrow stone steps between two terraces, the empty bamboo basket on her arm.", "She walks slowly down two steps with soft footfalls on stone; the terraces and the camera stay perfectly still.", 0.5, 0.55, props=["the basket"])
c(1, "terraces", "morning", "walk", [], "Close-up of a big rough pumpkin leaf on the trellis with heavy dew drops on it.", "One dew drop rolls slowly down the leaf and falls; the leaf trembles once and stays.")
c(1, "terraces", "morning", "walk", [], f"Close-up among the big pumpkin leaves on the ground: {PUMPKIN} resting on dry straw; her hands in undyed linen sleeves lift a leaf to show it.", "Her hands lift the leaf slowly and hold it; the pumpkin stays where it is.", 0.5, 0.6)
c(1, "terraces", "morning", "walk", [], f"Close-up of her hands in undyed linen sleeves knocking twice on {PUMPKIN} on the straw, listening.", "Her knuckles knock twice on the pumpkin with a hollow sound; the pumpkin stays still.")
c(1, "terraces", "morning", "walk", [], f"Close-up of her hands in undyed linen sleeves twisting the dry curled stalk of {PUMPKIN} until it snaps free of the vine.", "She twists the stalk slowly and it snaps off the vine with a dry crack.", 0.5, 0.45)
c(1, "terraces", "morning", "walk", E, f"Ellie seen from the side on the terrace, head bowed, lifting {PUMPKIN} from the straw in both arms.", "She lifts the pumpkin slowly against her chest and straightens up; the camera stays locked off.", 0.45, 0.5)
c(1, "terraces", "morning", "walk", [], "Close-up of a row of spring onions in dark soil; her fingers in undyed linen sleeves pull up three of them.", "She pulls the spring onions up slowly, a little soil falling from the white roots.")
c(1, "terraces", "morning", "walk", [], "Close-up of the bamboo basket on the mossy top of a dry-stone wall outdoors, the dusty-orange pumpkin in it and three spring onions beside it.", "Her hand lays the spring onions in the basket and draws back; the pumpkin stays where it is.", props=["the basket"])
c(1, "terraces", "morning", "walk", [], "Close-up of Pip the cat sitting on the mossy dry-stone wall of the terrace in the mist.", "Pip blinks slowly and his ear turns toward a sound; the wall and the mist stay still.", props=["Pip"])
s(1, "terraces", "morning", "Close-up of the bamboo grove at the top of the slope in the mist: tall green stems, thin leaves, a narrow earth path between them, no person.")
c(1, "terraces", "morning", "walk", [], "Close-up of the tall green bamboo stems at the top of the terraces in the mist, thin leaves above.", "Only the bamboo leaves sway and rustle softly in the breeze; nothing else moves and no one walks in.", 0.5, 0.4)

# ii. the spring
s(2, "spring", "late morning", "Close-up of the stone spring basin under the bamboo, no person: clear water running from the split bamboo pipe into the mossy stone trough, ferns around it.", 5.0, chapter=True)
c(2, "spring", "late morning", "walk", [], "Close-up of the split bamboo pipe pouring a thin clear stream into the mossy stone trough.", "Only the water moves, falling into the trough and rippling; nothing else moves.")
c(2, "spring", "late morning", "walk", [], "Close-up of the stone trough: her hands in rolled undyed linen sleeves wash the soil off the dusty-orange pumpkin under the running water.", "Her hands turn the pumpkin slowly under the water and the soil washes away.", 0.5, 0.55)
c(2, "spring", "late morning", "walk", [], "Close-up of her hands rinsing the three spring onions in the clear stream from the bamboo pipe.", "The water runs over the white roots and the last soil rinses off.")
c(2, "spring", "late morning", "walk", E, "Ellie seen from behind crouching at the stone trough under the bamboo, head bowed, the clean wet pumpkin on the flat stone beside her.", "She shakes the water from her hands slowly; the bamboo and the camera stay still.", 0.5, 0.5)

# iii. the stove
s(3, "kitchen", "afternoon", "Wide view of the plain kitchen with nobody in it: the clean dusty-orange pumpkin on the worn worktop, the clay stove, the lattice window open onto the valley.", 5.0, chapter=True)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the open fire door of the clay-brick stove: her hand in a rolled linen sleeve feeds in a few dry split sticks.", "The sticks catch with a soft crackle and small flames lick up; her hand draws back.", 0.5, 0.55)
c(3, "kitchen", "afternoon", "kitchen", [], "Top-down close-up of the worn worktop: the dusty-orange pumpkin already cut into thick wedges with bright orange flesh and a hollow of pale seeds; her hands lift one wedge.", "Her hands slowly lift one wedge and turn it to show the seeds; the other wedges stay where they are.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of her fingers in rolled linen sleeves scooping the pale wet seeds out of a bright orange pumpkin wedge into a small stoneware bowl.", "Her fingers scoop the seeds slowly and they drop into the bowl with a wet sound.")
c(3, "spring", "afternoon", "kitchen", [], "Close-up of the small stoneware bowl at the stone spring trough outdoors: her hands rinse the pale pumpkin seeds under the bamboo pipe, rubbing off the orange strings.", "The water runs through the seeds and her fingers rub them slowly.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the wide black iron pan on the clay stove: her hand tips the clean pale pumpkin seeds from the bowl into the dry hot pan.", "The seeds spill into the pan with a sharp patter and a little steam rises.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the wide black iron pan: pale pumpkin seeds toasting, her hand stirring them slowly with a flat wooden paddle.", "The paddle turns the seeds slowly; a few seeds pop and jump with a small crack.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the iron pan: thick bright orange pumpkin wedges laid flesh-down in a little oil, just starting to brown at the edges.", "The wedges sizzle softly and a thin curl of steam rises; the wedges stay where they are.")
c(3, "kitchen", "afternoon", "kitchen", E, "Ellie seen from the side at the clay stove, head bowed over the wide iron pan, turning the pumpkin wedges with long wooden chopsticks.", "She turns one wedge slowly with the chopsticks; smoke from the fire drifts past the lattice window; the camera stays locked off.", 0.45, 0.5)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of Pip the cat lying on the worn floorboards near the warm clay stove.", "Pip stretches one white paw slowly and settles again; nothing else moves.", props=["Pip"])
s(3, "kitchen", "afternoon", "Close-up of the lattice window open onto the valley: the hills in soft afternoon light, a few clouds, a stoneware jar on the sill, no person.")

# iv. the soup and the cakes
s(4, "kitchen", "afternoon", "Top-down close-up of the worn worktop: soft roasted pumpkin wedges with browned edges on a plain stoneware plate, a little steam rising, a small bowl of toasted pumpkin seeds beside it.", 5.0, chapter=True)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of her hands in rolled linen sleeves peeling the thin skin off a soft roasted pumpkin wedge with her fingers over a stoneware bowl.", "The skin peels away slowly and the soft orange flesh drops into the bowl.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the stoneware bowl of soft roasted orange pumpkin: her hand presses it into a smooth mash with a wooden pestle.", "The pestle presses down slowly and the pumpkin squashes into a soft orange mash.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a black clay pot on the stove: her hand tips spoonfuls of orange pumpkin mash into simmering water.", "The mash slides in with a soft plop and the water turns orange; steam rises.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the black clay pot of thick orange pumpkin soup bubbling gently, steam rising.", "Bubbles rise slowly through the thick soup with a soft blub; the pot stays still.", 0.5, 0.55)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a wide stoneware bowl: orange pumpkin mash with white flour; her hands knead it into a soft orange dough.", "Her hands fold and press the dough slowly; a little flour dusts the bowl.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the floured worktop: her palms press small balls of orange pumpkin dough into flat round cakes and set them in a row.", "She presses one ball flat slowly with her palm and lays it beside the others.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of her fingers pressing a few toasted pumpkin seeds into the top of each flat orange pumpkin cake on the floured worktop.", "Her fingers press the seeds in slowly one by one; the cakes stay in their row.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the wide black iron pan: flat orange pumpkin cakes with seeds on top frying in a little oil.", "The cakes sizzle steadily and their edges turn golden; a thin steam rises.", 0.5, 0.55)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the iron pan: her chopsticks turn one pumpkin cake over to show a crisp golden-brown underside.", "The cake flips slowly and lands with a sizzle.")
c(4, "kitchen", "afternoon", "kitchen", E, "Ellie seen from behind at the lattice window, wiping her hands slowly on her indigo apron while steam rises from the pot on the stove beside her.", "She wipes her hands slowly and looks out at the valley; the camera stays still.", 0.5, 0.45)

# v. the porch
s(5, "porch", "dusk", "Wide view of the small house from the terrace below at blue dusk: the deep eaves, the paper lamp lit on the porch, the misty valley, nobody outside.", 5.0, chapter=True)
c(5, "porch", "dusk", "supper", [], "Close-up of the low wooden table on the porch: her hands in oatmeal wool sleeves set down a plain stoneware bowl and a pair of wooden chopsticks.", "She sets the bowl down slowly and lays the chopsticks across it.")
c(5, "kitchen", "dusk", "supper", [], "Close-up of the black clay pot: a wooden ladle in her hand lifts thick orange pumpkin soup and pours it into a stoneware bowl.", "The soup pours slowly from the ladle into the bowl and steam rises.")
c(5, "porch", "dusk", "supper", [], "Top-down close-up of the stoneware bowl of thick orange pumpkin soup on the porch table: her fingers scatter toasted pumpkin seeds and a few green spring onion rings on top.", "The seeds and onion rings fall slowly onto the soup; steam rises.")
s(5, "porch", "dusk", "Top-down view of the low wooden porch table at dusk: the bowl of orange pumpkin soup with seeds on top, a plate of golden pumpkin cakes, a small cup of tea, wooden chopsticks, the light of the paper lamp from above.", 5.0)
c(5, "porch", "dusk", "supper", E, "Ellie seen from behind and a little to the side, sitting down on the low stool at the porch table, the blue misty valley beyond.", "She sits down slowly and tucks her cardigan around her; the lamp and the valley stay still; the camera stays locked off.")
c(5, "porch", "dusk", "supper", [], "Close-up of the plate of golden pumpkin cakes: her chopsticks pick one up and break it in half to show the soft orange inside.", "The cake breaks slowly with a soft crisp sound and a little steam rises.")
c(5, "porch", "dusk", "supper", [], "Close-up of the bowl of pumpkin soup: a porcelain spoon dips in and lifts thick orange soup with seeds.", "The spoon lifts slowly out of the soup and out of frame; steam rises.")
c(5, "porch", "dusk", "supper", [], "Close-up of Pip the cat curled on the second low stool on the porch, the light of the paper lamp on his fur.", "Pip breathes slowly and his ear twitches once; nothing else moves.", props=["Pip"])
c(5, "porch", "dusk", "supper", E, "Ellie seen from behind on the porch, holding the warm soup bowl in both hands, the blue valley and the first lights far below.", "She lifts the bowl a little in both hands and holds it; the valley and the lamp stay still.", 0.5, 0.45)
c(5, "porch", "dusk", "supper", [], "Wide view from the porch over the dark terraces into the blue misty valley at dusk, nobody anywhere.", "Only the mist moves slowly along the valley; nothing else moves and no one walks in.", 0.5, 0.5)

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
    "story_id": "fc-0521", "slug": "pumpkin-terraces", "title": "the sound of a pumpkin",
    "eyebrow": "a late autumn day", "season": "late autumn", "xf": 0.4,
    "style": style["id"], "camera": style["camera"], "grade": style["grade"], "music_lufs": style["music_lufs"],
    "shake": 2, "max_slow": 1.12,
    "light": light, "outfits": outfits, "places": places, "refs": refs,
    "chapters": [
        {"n": 1, "title": "i.  the terraces", "sub": "one knock, a hollow sound"},
        {"n": 2, "title": "ii.  the spring", "sub": "cold water, clean skin"},
        {"n": 3, "title": "iii.  the stove", "sub": "seeds and wedges"},
        {"n": 4, "title": "iv.  the dough", "sub": "soup, and little cakes"},
        {"n": 5, "title": "v.  the porch", "sub": "dinner above the mist"}],
    "beats": beats,
}
story["teaser"] = {
    "text": "Knock twice. If it sounds hollow, it's ready. This one was.", "text_secs": 5.5,
    "shots": [[find("knocking twice"), 0.5, 3.0], [find("tips the clean pale pumpkin seeds"), 0.6, 2.6],
              [find("turn one pumpkin cake over"), 0.8, 2.6], [find("thick orange pumpkin soup bubbling"), 1.0, 2.6],
              [find("walking slowly down the narrow stone steps"), 1.0, 2.8], [find("break it in half"), 1.0, 2.6],
              [find("Pip the cat curled"), 1.0, 2.4], [find("sitting down on the low stool"), 2.0, 3.6]]}
story["short"] = {
    "text": "one pumpkin, from the vine to dinner",
    "shots": [[find("knocking twice"), 0.5, 2.8, 0.5], [find("snaps free of the vine"), 0.8, 2.4, 0.5],
              [find("tips the clean pale pumpkin seeds"), 0.6, 2.4, 0.5], [find("turn one pumpkin cake over"), 0.8, 2.4, 0.5],
              [find("break it in half"), 1.0, 2.4, 0.5], [find("sitting down on the low stool"), 2.0, 3.0, 0.5]]}
Path("story.json").write_text(json.dumps(story, indent=1, ensure_ascii=False) + "\n")
print(len(beats), "beats", sum(b["kind"] == "clip" for b in beats), "clips")
