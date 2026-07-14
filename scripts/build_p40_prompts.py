#!/usr/bin/env python3
"""
Compose the per-principle condition prompts for the "p40" experiment:

  T_OFF        "Solve the following engineering problem."           (baseline)
  T_ON         "Use TRIZ to solve the following engineering problem."
  T_ON_P01..40 T_ON + a directive to apply the i-th Inventive Principle,
               with a one-paragraph explanation of that principle.
  T_ON_ALL40   T_ON + the full "40 Inventive Principles With Examples"
               document (Oxford Creativity) embedded as an attached
               reference. The attachment text is produced once by
               scripts/extract_p40_attachment.py from docs/*.pdf.

The 40 principle paragraphs are paraphrased/condensed from
jenson500/triz-prompt-engineering (MIT),
prompts/technical_triz/contradiction_solver_40_inventive_principles/40_Inventive_Principles_EN.md,
and length-controlled (~60-80 words each) so the 40 conditions do not vary
in prompt length among themselves.

Outputs:
  prompts/p40/T_OFF.txt, T_ON.txt, T_ON_P01.txt ... T_ON_P40.txt
  prompts/p40/principles/P01.txt ... P40.txt   (paragraph alone, for reuse
                                                by the adaptation checker)
Run:  python scripts/build_p40_prompts.py     (idempotent; prints word stats)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "prompts" / "p40"

T_OFF = "Solve the following engineering problem.\n"
T_ON = "Use TRIZ to solve the following engineering problem.\n"

# (name, paragraph). Paragraph = strategies in imperative form + brief examples.
PRINCIPLES = {
    1: ("Segmentation",
        "Divide the object or system into independent parts; make it easy to "
        "disassemble; separate parts according to a condition or parameter; "
        "increase the degree of fragmentation, down to the micro-level if useful. "
        "Examples: flat-pack furniture shipped as parts and assembled later; "
        "toothbrushes with replaceable heads; tables with foldable legs; magnetic "
        "powder ground ever finer to reveal field lines, and finer still to form "
        "a ferrofluid."),
    2: ("Separation",
        "Extract or separate the disturbing part or property from the object, or "
        "isolate the only necessary part or property and use it alone. Examples: "
        "a mechanical pencil separates the consumable lead from the durable body, "
        "so only the lead is replaced; a scarecrow reproduces only the necessary "
        "human characteristics (appearance and sound) needed to scare birds away, "
        "without a person having to guard the field."),
    3: ("Local Quality",
        "Move from a homogeneous structure to an inhomogeneous one; let different "
        "parts perform different functions; place each component under its own "
        "locally optimal conditions. Examples: socks with anti-slip studs only on "
        "the sole; shoelace ends reinforced with sleeves for threading; a heated "
        "blank cooled from the outside so it stays hard outside but soft inside, "
        "internally guiding the forming tool that passes through it."),
    4: ("Asymmetry",
        "Replace symmetrical forms with asymmetrical ones; if the object is "
        "already asymmetrical, increase the degree of asymmetry; change its shape "
        "to match asymmetries in the environment. Examples: connectors and memory "
        "cards shaped so they can only be inserted the correct way; a car tire "
        "with extra sidewall reinforcement on the outer side only; furniture with "
        "individually adjustable legs that stays level on uneven floors."),
    5: ("Merging",
        "Combine identical or cooperating objects in space; couple similar or "
        "related operations in time; group elements into bi- or poly-systems. "
        "Examples: catamarans and trimarans gain speed and stability by combining "
        "several hulls; a piezo lighter merges spark generation and gas release "
        "into a single action; a bicycle chain couples many links to transmit "
        "high force while staying flexible."),
    6: ("Universality",
        "Make one object perform multiple functions so that other objects or "
        "systems become unnecessary; use standardized, interchangeable features. "
        "Examples: an all-in-one device combining printer, scanner, copier and "
        "fax; a Swiss Army knife packing many tools into one; a standardized "
        "battery pack that powers drills, saws and grinders from the same "
        "manufacturer, replacing separate batteries per tool."),
    7: ("Nesting",
        "Place one object inside another, which in turn sits inside a third; let "
        "an object pass through a cavity of another; use telescoping structures. "
        "Examples: a foldable trekking cup that collapses into itself for "
        "transport; a travel toothbrush whose handle doubles as the protective "
        "cap for the head; telescopic pointers and car antennas that retract when "
        "not in use."),
    8: ("Anti-weight",
        "Compensate the object's weight by joining it to something that provides "
        "lift; use aerodynamic, hydrodynamic, buoyant, magnetic or other opposing "
        "forces from the environment. Examples: aircraft wings converting forward "
        "motion into lift; cargo drones with lifting wings that save battery "
        "power; underwater equipment built with buoyant frames for near-neutral "
        "buoyancy; furniture levitated above a magnetic base plate."),
    9: ("Preliminary Anti-action",
        "Precede the required action with an opposing action; when an action has "
        "both harmful and useful effects, apply countermeasures beforehand; if "
        "the object will be under load, pre-stress it in the opposite direction. "
        "Examples: a wind-up toy pulled backwards before it runs forward; "
        "probiotics taken alongside antibiotics to protect gut bacteria; a "
        "brittle shaft compressed along its axis before bending so it does not "
        "break."),
    10: ("Preliminary Action",
         "Perform the required change fully or partially in advance; pre-arrange "
         "objects so they can act immediately from the most convenient position. "
         "Examples: coffee capsules pre-dosed for exactly one cup; furniture "
         "pre-assembled at the factory so only a few final steps remain; "
         "pre-moistened cleaning wipes ready for immediate use; pop-up tents "
         "that unfold into shape in minutes."),
    11: ("In-advance Cushioning",
         "Compensate for the limited reliability of a system by preparing "
         "emergency countermeasures beforehand, so that when failure or overload "
         "occurs the damage is absorbed. Examples: a pressure relief valve that "
         "vents before a tank can burst; a car airbag that inflates into a gas "
         "cushion before the head strikes the steering wheel; a protective phone "
         "case that absorbs drops and impacts."),
    12: ("Equipotentiality",
         "Change the working conditions so the object need not be raised, "
         "lowered or rotated; keep potential energy constant; avoid peaks, "
         "spikes and harmful gradients, and create conditions that neutralize "
         "existing tensions. Examples: raised tram platforms for step-free "
         "boarding; a maintenance pit so vehicles need not be lifted; energy "
         "storage smoothing demand peaks; a conductive wristband preventing "
         "electrostatic charging."),
    13: ("The Other Way Around",
         "Invert the action: instead of the effect dictated by the task, aim for "
         "the opposite; make moving parts fixed and fixed parts moving; turn the "
         "object or process upside down. Examples: an ink eraser that removes "
         "ink instead of applying it; an escalator or treadmill where the "
         "surface moves and the person stays; leak-testing a tank by filling it "
         "with air and submerging it so bubbles reveal the leak."),
    14: ("Spheroidality and Curvature",
         "Replace straight contours with curves, flat surfaces with spherical "
         "ones; use rollers, balls and spirals; replace linear motion with "
         "rotation; exploit centrifugal force. Examples: a spherical mirror "
         "reflecting images from many directions at once; ball bearings turning "
         "sliding friction into low-friction rolling; the spark wheel of a "
         "lighter replacing a striking motion; a salad spinner using centrifugal "
         "force to fling water off the leaves."),
    15: ("Dynamization",
         "Design the system so it automatically adjusts to optimal conditions in "
         "each phase of operation; divide it into elements that can rearrange "
         "relative to each other; make rigid or immovable things movable, "
         "adjustable or interchangeable. Examples: height-adjustable desks for "
         "sitting or standing; a folding fan that is compact until unfolded; a "
         "wireless mouse freed from its cable; a toothbrush with a flexing neck "
         "that protects the gums."),
    16: ("Partial or Excessive Actions",
         "If achieving exactly 100 percent of the desired effect is hard, use "
         "slightly less or slightly more and then remove or tolerate the "
         "difference - this often simplifies the problem greatly. Examples: "
         "holes in a wall are overfilled with plaster and sanded smooth after "
         "hardening; parts are dip-coated and the excess paint is removed; an "
         "ink pad holds more ink than one stamping needs so the stamp can be "
         "used repeatedly."),
    17: ("Transition to Another Dimension",
         "Move from one dimension to two or three; arrange objects in multiple "
         "layers instead of one; tilt, reorient or lay the object on its side; "
         "use the reverse side or redirect light onto adjacent areas. Examples: "
         "a grater curved from flat into a multi-sided body; software windows "
         "stacked in layers on screen; logs stored vertically instead of piled; "
         "mirrors in orchards reflecting sunlight onto fruit from below."),
    18: ("Mechanical Vibration",
         "Set the object oscillating or vibrating; increase the frequency up to "
         "ultrasonic; use its resonant frequency; replace mechanical vibrators "
         "with piezoelectric ones; combine ultrasonic vibration with "
         "electromagnetic fields. Examples: ultrasonic baths that clean parts by "
         "vibrating the fluid; piezo vibrators that shake ice off radar domes; "
         "focused ultrasound that destroys tumors or kidney stones without "
         "incisions."),
    19: ("Periodic Action",
         "Replace a continuous action with periodic pulses; if the action is "
         "already periodic, change its frequency; use the pauses between pulses "
         "to perform other useful actions. Examples: a jackhammer breaking "
         "material with impulses; ABS brakes pulsing to keep steering control; "
         "a siren varying tone and amplitude to attract more attention; CPR "
         "alternating chest compressions with ventilation in the pauses."),
    20: ("Continuity of Useful Action",
         "Carry out the work without interruption, with all parts operating at "
         "constant full load; eliminate idle running and dead intervals; replace "
         "back-and-forth motion with rotation. Examples: inkjet printers that "
         "print on both directions of the carriage stroke; a revolving door "
         "passing people continuously in both directions; an aircraft APU "
         "running constantly at peak efficiency; operating systems doing cleanup "
         "during idle time."),
    21: ("Skipping",
         "Perform harmful, hazardous or delicate stages at very high speed, so "
         "fast that damage has no time to develop. Examples: thin-walled plastic "
         "tubes cut at very high speed so inertia keeps them from deforming; a "
         "finger moved quickly through a flame without being burned; a flip book "
         "whose rapidly turned pages merge into fluid motion."),
    22: ("Blessing in Disguise",
         "Use harmful factors or effects of the environment to obtain a positive "
         "effect; cancel one harmful factor by combining it with another; "
         "amplify a harmful factor until it ceases to be harmful. Examples: "
         "regenerative braking charging the battery; power-plant waste heat "
         "warming houses; weakened viruses used as vaccines; a controlled "
         "backfire stopping a forest fire; acids and alkalis alternated in one "
         "pipe so each limits the other's damage."),
    23: ("Feedback",
         "Introduce feedback so the system's output regulates its own action; if "
         "feedback already exists, change its magnitude, sensitivity or "
         "direction. Examples: a heating thermostat that opens or closes the "
         "valve depending on room temperature; a check valve whose flap responds "
         "to flow direction; smart lighting that adjusts brightness and color "
         "temperature to the time of day and residents' activity."),
    24: ("Intermediary",
         "Introduce an intermediate object that transmits, carries out or passes "
         "on the action; temporarily join the object to another that is easy to "
         "remove afterwards. Examples: protective gloves mediating between hand "
         "and hazard while transferring grip; a V-belt carrying one motor's "
         "power to several consumers; a magnetic charging connector that holds "
         "securely yet detaches safely when the cable is yanked."),
    25: ("Self-service",
         "Make the object serve itself, performing its own auxiliary, repair and "
         "maintenance functions; make use of waste material, waste energy and "
         "by-products. Examples: a lock nut whose deformed plastic ring secures "
         "itself against loosening; a calculator powered by its own solar cell; "
         "manure used as fertilizer; braking energy or scrap metal recovered and "
         "fed back into the process."),
    26: ("Copying",
         "Use a simplified, cheap copy instead of a complex, expensive or "
         "fragile object; replace the object with its optical or digital image "
         "and work on that; move on to infrared, ultraviolet or X-ray images if "
         "needed. Examples: e-books replacing printed volumes; counting fish on "
         "a photograph where they stand still; thermal cameras visualizing "
         "temperature; X-rays revealing voids inside metal parts."),
    27: ("Cheap Short-living Objects",
         "Replace one expensive, durable object with a set of cheap, short-lived "
         "ones, accepting the loss of some qualities such as longevity. "
         "Examples: paper tissues replacing cloth handkerchiefs; one-day contact "
         "lenses instead of costly long-wear lenses; disposable razors built as "
         "simply as possible to minimize development and production cost; "
         "sterile single-use syringes and needles discarded after each "
         "injection."),
    28: ("Mechanics Substitution",
         "Replace the mechanical system with an optical, acoustic, thermal or "
         "chemical one; use electric, magnetic or electromagnetic fields; move "
         "from static to moving or structured fields; combine fields with "
         "field-activated particles. Examples: a laser rangefinder replacing the "
         "tape measure; radio keys replacing mechanical car keys; electromagnets "
         "levitating parts along an assembly line; magnetic nanoparticles "
         "steering drugs to a tumor."),
    29: ("Pneumatics and Hydraulics",
         "Replace heavy or rigid parts with gas or liquid: use inflatable or "
         "fluid-filled elements, air cushions and hydrostatic cushions. "
         "Examples: bubble wrap protecting fragile goods; air-filled tires that "
         "roll easily while absorbing shocks; airbags supplementing rigid seat "
         "belts; hydraulic brakes responding faster and more precisely than "
         "mechanical linkages; liquid cooling outperforming a passive heat "
         "sink."),
    30: ("Flexible Shells and Thin Films",
         "Replace rigid three-dimensional constructions with flexible shells, "
         "membranes or thin films; isolate the object from its environment with "
         "a thin film; increase the degree of flexibility. Examples: thin "
         "plastic bottles replacing heavy breakable glass; flexible thin-film "
         "solar panels conforming to curved roofs; a tea bag separating leaves "
         "from water through a permeable fleece; vacuum bags compressing stored "
         "items."),
    31: ("Porous Materials",
         "Make the object porous or add porous elements such as inserts and "
         "coatings; if it is already porous, fill the pores in advance with a "
         "useful substance. Examples: foam full of air pockets used for "
         "cushioning and mattresses; lightweight sandwich panels with rigid-foam "
         "cores; activated-carbon filters trapping contaminants in their pores; "
         "a temperature-resistant porous rod pre-soaked with alloying agents for "
         "molten metal."),
    32: ("Color Changes",
         "Change the color or transparency of the object or its surroundings; "
         "add color indicators to observe what is hard to see; use luminescent "
         "or fluorescent tracers; change emission properties under radiant heat. "
         "Examples: red darkroom light that spares the film; transparent lighter "
         "tanks showing the gas level; toothbrush bristles whose fading color "
         "signals replacement; pH strips; fluorescent dye under UV revealing "
         "hairline cracks."),
    33: ("Homogeneity",
         "Make objects that interact with each other out of the same material, "
         "or one with very similar properties, to avoid mismatch, wear and "
         "contamination. Examples: wooden dowels joining wooden furniture so "
         "neither part damages the other; rivets of the same metal as the parts "
         "to prevent corrosion; ice cubes frozen from the drink itself so it is "
         "never diluted; biodegradable bags composted together with the organic "
         "waste inside."),
    34: ("Discarding and Recovering",
         "Discard, dissolve or evaporate parts of the system once they have "
         "fulfilled their function, or restore consumable parts directly during "
         "operation. Examples: spent cartridge cases ejected to make room for "
         "the next round; booster rockets dropped at altitude and recovered for "
         "reuse; snap-off blades broken away to expose a fresh edge; "
         "rechargeable batteries regenerated by recharging."),
    35: ("Parameter Changes",
         "Change the object's physical state (solid, liquid, gas or quasi-state), "
         "its concentration, consistency, flexibility, temperature, volume, "
         "pressure or other parameters, or change the surrounding medium to an "
         "optimal setting. Examples: natural gas liquefied for compact transport; "
         "fuel paste replacing spillable liquid alcohol; a glue stick soft for "
         "application then hardening; a self-cooling beer keg using evaporative "
         "cooling into zeolite."),
    36: ("Phase Transitions",
         "Exploit the effects that accompany phase transitions: volume changes, "
         "absorption or release of heat, and related phenomena. Examples: gel "
         "heat packs that release the latent heat of crystallization when a "
         "supercooled salt solution is triggered, and recharge in hot water; "
         "heat pumps that heat or cool buildings efficiently by cycling a "
         "working fluid through evaporation and condensation."),
    37: ("Thermal Expansion",
         "Use the thermal expansion or contraction of materials; combine several "
         "materials with different thermal expansion coefficients. Examples: "
         "shrink tubing that tightens around conductors when heated; a liquid "
         "thermometer reading temperature from the expansion of its fluid; a "
         "bimetallic strip thermostat bending as temperature changes to control "
         "radiators; glass-ceramic cooktops engineered for near-zero expansion; "
         "conical rings with differing coefficients compensating a bearing gap "
         "across temperatures."),
    38: ("Strong Oxidants",
         "Intensify the process by enriching the atmosphere: replace ordinary "
         "air with oxygen-enriched air, enriched air with pure oxygen; expose "
         "air or oxygen to ionizing radiation; use ionized oxygen or ozone. "
         "Examples: oxidizing cleaners lifting stains better than plain "
         "detergent; pure oxygen blown through molten pig iron to make steel; "
         "air ionizers making dust settle; ozone generators destroying odor "
         "molecules."),
    39: ("Inert Atmosphere",
         "Replace the normal environment with an inert one; carry out the "
         "process in a vacuum; add neutral substances or inert additives to the "
         "object. Examples: argon shielding the welding zone from oxidation; "
         "inert gas in incandescent bulbs protecting the filament; vacuum-packed "
         "food staying fresh far longer; shaving foam interposing a slow, "
         "protective medium between blade and skin; foam absorbing sound in "
         "speakers."),
    40: ("Composite Materials",
         "Replace a homogeneous material with a composite that combines "
         "components whose joint properties none of them has alone. Examples: "
         "carbon-fiber-reinforced plastic aircraft wings that are stronger than "
         "aluminum yet far lighter and corrosion-resistant; fiberglass boats and "
         "surfboards lighter and easier to shape than wood; Tetra Pak cartons "
         "layering cardboard for stiffness, polyethylene for sealing and "
         "aluminum as a light barrier."),
}

DIRECTIVE = (
    "In your solution, apply TRIZ Inventive Principle {n}: {name}.\n"
    "{para}\n"
    "Base your solution on this principle, adapting it to the specifics of the problem.\n"
)

ATTACHMENT = ROOT / "prompts" / "p40" / "attachments" / "40_principles_oxford.txt"

ALL40_DIRECTIVE = (
    "In your solution, apply TRIZ's 40 Inventive Principles. The full reference "
    "document is attached below. Choose whichever principles best fit the problem "
    "and base your solution on them, adapting them to the specifics of the problem.\n"
    "\n"
    "--- ATTACHED REFERENCE: 40 Inventive Principles With Examples ---\n"
    "{attachment}\n"
    "--- END OF ATTACHED REFERENCE ---\n"
)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "principles").mkdir(exist_ok=True)

    (OUT / "T_OFF.txt").write_text(T_OFF)
    (OUT / "T_ON.txt").write_text(T_ON)

    words = []
    for n, (name, para) in sorted(PRINCIPLES.items()):
        (OUT / "principles" / f"P{n:02d}.txt").write_text(
            f"Principle {n}: {name}\n{para}\n")
        body = T_ON + "\n" + DIRECTIVE.format(n=n, name=name, para=para)
        (OUT / f"T_ON_P{n:02d}.txt").write_text(body)
        words.append((n, name, len(para.split()), len(body.split())))

    if ATTACHMENT.exists():
        all40 = T_ON + "\n" + ALL40_DIRECTIVE.format(attachment=ATTACHMENT.read_text().strip())
        (OUT / "T_ON_ALL40.txt").write_text(all40)
        print(f"wrote T_ON_ALL40.txt ({len(all40.split())} words, from {ATTACHMENT.name})")
    else:
        print(f"NOTE: {ATTACHMENT} missing - run scripts/extract_p40_attachment.py first; "
              "T_ON_ALL40.txt not built")

    ws = [w for _, _, w, _ in words]
    print(f"wrote {len(words)} principle prompts -> {OUT}")
    print(f"paragraph words: min={min(ws)} max={max(ws)} mean={sum(ws)/len(ws):.1f}")
    for n, name, w, tot in words:
        flag = "  <-- outlier" if w < 55 or w > 90 else ""
        print(f"  P{n:02d} {name:32s} para={w:3d}w  full-prompt={tot:3d}w{flag}")


if __name__ == "__main__":
    main()
