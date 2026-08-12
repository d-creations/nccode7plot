"""Modal M-code handling for Star turning machines."""

from ncplot7py.domain.handlers.mcode_modal import BaseModalMCodeHandler


class StarModalMCodeHandler(BaseModalMCodeHandler):
    c_axis_reset_codes = {"M3", "M4", "M9"}


__all__ = ["StarModalMCodeHandler"]