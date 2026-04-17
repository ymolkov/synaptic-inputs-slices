const stages = {
    protocol: {
        image: "assets/site/method-protocol.png",
        alt: "Representative current-clamp and voltage-clamp step protocols aligned with XII respiratory activity.",
        kicker: "Stage 01",
        title: "Stepped acquisition supplies the I-V spread.",
        description:
            "Current-clamp and voltage-clamp command levels are held piecewise constant while the slice continues to cycle. The analysis uses the whole accepted interval rather than a single step.",
        input: "Aligned current, voltage, and XII traces",
        output: "Usable command epochs across many cycles"
    },
    phase: {
        image: "assets/site/method-protocol.png",
        alt: "Expanded recording excerpts with command transitions and respiratory-cycle reference traces.",
        kicker: "Stage 02",
        title: "Cycle timing becomes a normalized phase axis.",
        description:
            "XII burst onsets define phase zero. Samples between onsets are mapped onto a 0 to 1 cycle, letting variable-duration breaths contribute to the same phase-resolved analysis.",
        input: "Detected XII cycle onsets",
        output: "Respiratory phase assigned to every retained sample"
    },
    wedge: {
        image: "assets/site/method-workflow.png",
        alt: "Geometric inference figure with phase-binned I-V regressions and wedge boundaries.",
        kicker: "Stage 03",
        title: "Phase-binned regressions form a geometric wedge.",
        description:
            "Each phase bin gets a robust I-V fit. The fitted slope and intercept trace a wedge whose upper boundary estimates the inhibitory reversal potential for that recording.",
        input: "Per-phase I-V point clouds",
        output: "G_tot, I0, and recording-specific E_i"
    },
    conductance: {
        image: "assets/site/conductance-profiles.png",
        alt: "Representative excitatory and inhibitory conductance profiles for VgluT2 and VGAT populations.",
        kicker: "Stage 04",
        title: "The mixed current separates into excitatory and inhibitory conductance.",
        description:
            "Leak-only limits at the excitatory and inhibitory reversal potentials anchor the decomposition. Outputs are reported as G_exc/g_leak and G_inh/g_leak.",
        input: "Wedge geometry plus leak estimate",
        output: "Phase-resolved excitatory and inhibitory traces"
    },
    circuit: {
        image: "assets/site/circuit-weighted.png",
        alt: "Conductance-weighted inferred circuit diagram for inspiratory and expiratory populations.",
        kicker: "Stage 05",
        title: "Conductance fingerprints become a population circuit.",
        description:
            "Phase-specific conductance means identify the functional drives between VgluT2-I, VgluT2-E, VGAT-I, and VGAT-E populations, with edge weights scaled by normalized conductance.",
        input: "Population summary conductances",
        output: "Inferred excitatory kernel and inhibitory connectome"
    }
};

const buttons = Array.from(document.querySelectorAll("[data-stage]"));
const image = document.getElementById("stage-image");
const kicker = document.getElementById("stage-kicker");
const title = document.getElementById("stage-title");
const description = document.getElementById("stage-description");
const input = document.getElementById("stage-input");
const output = document.getElementById("stage-output");

function setStage(stageName) {
    const stage = stages[stageName];
    if (!stage) {
        return;
    }

    buttons.forEach((button) => {
        const active = button.dataset.stage === stageName;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
    });

    image.src = stage.image;
    image.alt = stage.alt;
    kicker.textContent = stage.kicker;
    title.textContent = stage.title;
    description.textContent = stage.description;
    input.textContent = stage.input;
    output.textContent = stage.output;
}

buttons.forEach((button) => {
    button.addEventListener("click", () => setStage(button.dataset.stage));
});
