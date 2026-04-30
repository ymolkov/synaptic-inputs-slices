const stages = {
    record: {
        image: "assets/site/method-protocol.png",
        alt: "Representative current-clamp and voltage-clamp command steps aligned to a respiratory cycle reference.",
        kicker: "Step 01",
        title: "Record across command levels while the network keeps cycling.",
        description:
            "Current-clamp and voltage-clamp files provide the same ingredients: a current coordinate, a voltage coordinate, and a cycle reference. SCION uses the full accepted interval rather than treating each step as a separate experiment.",
        input: "current, voltage, time, phase reference",
        output: "samples spanning many cycles and command levels"
    },
    clock: {
        image: "assets/site/method-protocol.png",
        alt: "Expanded recording excerpts with command transitions and a respiratory cycle reference trace.",
        kicker: "Step 02",
        title: "Turn the reference signal into phase.",
        description:
            "Cycle onsets define phase zero. Every sample is assigned a normalized phase between successive onsets, so slower and faster cycles can contribute to the same within-cycle map.",
        input: "reference burst, stimulus pulse, or other cycle marker",
        output: "phase assigned to every retained sample"
    },
    fit: {
        image: "assets/site/method-workflow.png",
        alt: "Phase-binned current-voltage regressions used for conductance inference.",
        kicker: "Step 03",
        title: "Fit a local I-V relationship at each phase.",
        description:
            "Samples from many cycles and command levels are pooled by phase. Each phase bin gets a robust I-V regression whose slope and intercept describe the total conductance state at that moment of the network cycle.",
        input: "phase-binned I-V point clouds",
        output: "G_tot and I0 as functions of phase"
    },
    separate: {
        image: "assets/site/method-workflow.png",
        alt: "Wedge geometry used to separate excitatory and inhibitory conductance.",
        kicker: "Step 04",
        title: "Use reversal geometry to separate the mixed synaptic drive.",
        description:
            "The slope-intercept trajectory forms a wedge. Its envelope estimates the inhibitory boundary for the recording, and the resulting geometry separates dynamic excitation from dynamic inhibition.",
        input: "slope-intercept trajectory plus reversal potentials",
        output: "G_exc/g_leak and G_inh/g_leak over phase"
    },
    compare: {
        image: "assets/site/circuit-weighted.png",
        alt: "Conductance-weighted inferred circuit diagram for inspiratory and expiratory populations.",
        kicker: "Step 05",
        title: "Compare conductance profiles across identified cells.",
        description:
            "Once each recording has a phase-resolved excitatory and inhibitory profile, populations can be compared by identity, phase preference, preparation, perturbation, or experimental condition.",
        input: "per-recording conductance profiles",
        output: "population summaries and functional circuit hypotheses"
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
