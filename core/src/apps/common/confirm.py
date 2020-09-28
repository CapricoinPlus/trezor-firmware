from trezor import wire
from trezor.messages import ButtonRequestType
from trezor.ui.model import lookup_layout
from trezor.ui.model.tt.confirm import (
    CONFIRMED,
    INFO,
    Confirm,
    HoldToConfirm,
    InfoConfirm,
)

from . import button_request

if __debug__:
    from trezor.ui.model.tt.scroll import Paginated


if False:
    from typing import Any, Callable, Optional, Union, List, Dict
    from trezor import ui
    from trezor.ui.model.tt.confirm import ButtonContent, ButtonStyleType
    from trezor.ui.loader import LoaderStyleType
    from trezor.messages.ButtonRequest import EnumTypeButtonRequestType


async def confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: Optional[ButtonContent] = Confirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = Confirm.DEFAULT_CONFIRM_STYLE,
    cancel: Optional[ButtonContent] = Confirm.DEFAULT_CANCEL,
    cancel_style: ButtonStyleType = Confirm.DEFAULT_CANCEL_STYLE,
    major_confirm: bool = False,
) -> bool:
    await button_request(ctx, code=code)

    if content.__class__.__name__ == "Paginated":
        # The following works because asserts are omitted in non-debug builds.
        # IOW if the assert runs, that means __debug__ is True and Paginated is imported
        assert isinstance(content, Paginated)

        content.pages[-1] = Confirm(
            content.pages[-1],
            confirm,
            confirm_style,
            cancel,
            cancel_style,
            major_confirm,
        )
        dialog = content  # type: ui.Layout
    else:
        dialog = Confirm(
            content, confirm, confirm_style, cancel, cancel_style, major_confirm
        )

    return await ctx.wait(dialog) is CONFIRMED


async def info_confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    info_func: Callable,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: ButtonContent = InfoConfirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = InfoConfirm.DEFAULT_CONFIRM_STYLE,
    cancel: ButtonContent = InfoConfirm.DEFAULT_CANCEL,
    cancel_style: ButtonStyleType = InfoConfirm.DEFAULT_CANCEL_STYLE,
    info: ButtonContent = InfoConfirm.DEFAULT_INFO,
    info_style: ButtonStyleType = InfoConfirm.DEFAULT_INFO_STYLE,
) -> bool:
    await button_request(ctx, code=code)

    dialog = InfoConfirm(
        content, confirm, confirm_style, cancel, cancel_style, info, info_style
    )

    while True:
        result = await ctx.wait(dialog)

        if result is INFO:
            await info_func(ctx)

        else:
            return result is CONFIRMED


async def hold_to_confirm(
    ctx: wire.GenericContext,
    content: ui.Component,
    code: EnumTypeButtonRequestType = ButtonRequestType.Other,
    confirm: str = HoldToConfirm.DEFAULT_CONFIRM,
    confirm_style: ButtonStyleType = HoldToConfirm.DEFAULT_CONFIRM_STYLE,
    loader_style: LoaderStyleType = HoldToConfirm.DEFAULT_LOADER_STYLE,
    cancel: bool = True,
) -> bool:
    await button_request(ctx, code=code)

    if content.__class__.__name__ == "Paginated":
        # The following works because asserts are omitted in non-debug builds.
        # IOW if the assert runs, that means __debug__ is True and Paginated is imported
        assert isinstance(content, Paginated)

        content.pages[-1] = HoldToConfirm(
            content.pages[-1], confirm, confirm_style, loader_style, cancel
        )
        dialog = content  # type: ui.Layout
    else:
        dialog = HoldToConfirm(content, confirm, confirm_style, loader_style, cancel)

    return await ctx.wait(dialog) is CONFIRMED


async def require_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled


async def require_hold_to_confirm(*args: Any, **kwargs: Any) -> None:
    confirmed = await hold_to_confirm(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled


# code using the functions above ^^^ should migrate to the interface below vvv

# fmt: off
_type_to_code = {
    "confirm_backup1":                     ButtonRequestType.ResetDevice,
    "confirm_backup2":                     ButtonRequestType.ResetDevice,
    "confirm_change_count_over_threshold": ButtonRequestType.SignTx,
    "confirm_feeoverthreshold":            ButtonRequestType.FeeOverThreshold,
    "confirm_joint_total":                 ButtonRequestType.SignTx,
    "confirm_nondefault_locktime":         ButtonRequestType.SignTx,
    "confirm_output":                      ButtonRequestType.ConfirmOutput,
    "confirm_path_warning":                ButtonRequestType.UnknownDerivationPath,
    "confirm_ping":                        ButtonRequestType.ProtectCall,
    "confirm_reset_device":                ButtonRequestType.ResetDevice,
    "confirm_total":                       ButtonRequestType.SignTx,
    "confirm_wipe":                        ButtonRequestType.WipeDevice,
    "show_address":                        ButtonRequestType.Address,
    "show_qr":                             ButtonRequestType.Address,
    "warn_loading_seed":                   ButtonRequestType.Other,
}  # type: Dict[str, EnumTypeButtonRequestType]
# fmt: on


async def interact(
    ctx: wire.GenericContext, brtype: str, **content: Union[str, List[str]],
) -> bool:
    code = _type_to_code.get(
        brtype, ButtonRequestType.Other
    )  # FIXME: throw exception instead?
    await button_request(ctx, code=code)

    dialog = lookup_layout(brtype, content)

    return await ctx.wait(dialog) is CONFIRMED


async def require_interact(*args: Any, **kwargs: Any) -> None:
    confirmed = await interact(*args, **kwargs)
    if not confirmed:
        raise wire.ActionCancelled
