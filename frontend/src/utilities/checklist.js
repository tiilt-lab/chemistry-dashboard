// The metric/feature toggle checklists used by the expert-rating,
// student-dashboard and BYOD-join dashboards — previously three verbatim
// copies of these arrays plus the init loop.

export const FEATURE_LABELS = [
    "Emotional tone",
    "Analytic thinking",
    "Clout",
    "Authenticity",
    "Confusion",
    "Participation",
    "Social Impact",
    "Responsivity",
    "Internal Cohesion",
    "Newness",
    "Communication Density",
    "Attention Level",
    "Facial Emotions",
    "Object Focused On",
]

export const BOX_LABELS = [
    "Timeline control",
    "Participation",
    "Social Impact",
    "Responsivity",
    "Internal Cohesion",
    "Newness",
    "Communication Density",
    "Video Metrics",
]

export function buildChecklist(labels) {
    return labels.map((label, value) => ({ label, value, clicked: true }))
}
