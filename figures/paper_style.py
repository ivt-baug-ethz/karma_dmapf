"""Shared controller styles for the paper figures.

The colours are from the Okabe-Ito scheme, which stays distinguishable under deuteranopia,
protanopia and tritanopia. Four colours cannot all differ in grey tone, so every controller also
has its own marker and hatch for greyscale prints. Karma gets the orange so it stands out.
"""

CONTROLLER_COLORS = {
    "DECENTRALIZED_TOKEN_PASSING": "#000000",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "#0072B2",
    "DECENTRALIZED_NEGOTIATE_UTILITARIAN": "#009E73",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "#D55E00",
}

CONTROLLER_MARKERS = {
    "DECENTRALIZED_TOKEN_PASSING": "D",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "^",
    "DECENTRALIZED_NEGOTIATE_UTILITARIAN": "s",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "o",
}

CONTROLLER_HATCHES = {
    "DECENTRALIZED_TOKEN_PASSING": "xxx",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "\\\\\\",
    "DECENTRALIZED_NEGOTIATE_UTILITARIAN": "///",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "",
}
