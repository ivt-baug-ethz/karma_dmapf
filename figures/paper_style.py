"""Shared controller styles for the paper figures.

The colours are Paul Tol's muted scheme, which stays distinguishable under deuteranopia,
protanopia and tritanopia. Four colours cannot all differ in grey tone, so every controller also
has its own marker and hatch for greyscale prints. Karma gets the darkest colour; Karma and
Altruistic, the pair compared most, are furthest apart in lightness.
"""

CONTROLLER_COLORS = {
    "DECENTRALIZED_TOKEN_PASSING": "#CC6677",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "#117733",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "#999933",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "#332288",
}

CONTROLLER_MARKERS = {
    "DECENTRALIZED_TOKEN_PASSING": "D",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "^",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "s",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "o",
}

CONTROLLER_HATCHES = {
    "DECENTRALIZED_TOKEN_PASSING": "xxx",
    "DECENTRALIZED_NEGOTIATE_EGOISTIC": "\\\\\\",
    "DECENTRALIZED_NEGOTIATE_ALTRUISTIC": "///",
    "DECENTRALIZED_NEGOTIATE_TRIP_KARMA": "",
}
