from trezor import wire

from apps.common import HARDENED, paths
from apps.common.keychain import get_keychain

from . import CURVE, networks

if False:
    from typing import Callable, Iterable
    from typing_extensions import Protocol

    from protobuf import MessageType

    from trezor.messages.EthereumSignTx import EthereumSignTx

    from apps.common.keychain import MsgOut, Handler, HandlerWithKeychain

    class MsgWithAddressN(MessageType, Protocol):
        address_n = ...  # type: paths.Bip32Path


# We believe Ethereum should use 44'/60'/a' for everything, because it is
# account-based, rather than UTXO-based. Unfortunately, lot of Ethereum
# tools (MEW, Metamask) do not use such scheme and set a = 0 and then
# iterate the address index i. Therefore for compatibility reasons we use
# the same scheme: 44'/60'/0'/0/i and only the i is being iterated.

PATTERN_ADDRESS_COMPAT = "m/44'/coin_type'/0'/0/address_index"
PATTERN_PUBKEY = "m/44'/coin_type'/account'/*"

PATTERNS_ADDRESS = (PATTERN_ADDRESS_COMPAT, paths.PATTERN_SEP5)


def _schemas_from_address_n(
    patterns: Iterable[str], address_n: paths.Bip32Path
) -> Iterable[paths.PathSchema]:
    if len(address_n) < 2:
        return ()

    slip44_hardened = address_n[1]
    if slip44_hardened not in networks.all_slip44_ids_hardened():
        return ()

    if not slip44_hardened & HARDENED:
        return ()

    slip44_id = slip44_hardened - HARDENED
    return (paths.PathSchema(pattern, slip44_id) for pattern in patterns)


def with_keychain_from_path(
    *patterns: str,
) -> Callable[
    [HandlerWithKeychain[MsgWithAddressN, MsgOut]], Handler[MsgWithAddressN, MsgOut]
]:
    def decorator(
        func: HandlerWithKeychain[MsgWithAddressN, MsgOut]
    ) -> Handler[MsgWithAddressN, MsgOut]:
        async def wrapper(ctx: wire.Context, msg: MsgWithAddressN) -> MsgOut:
            schemas = _schemas_from_address_n(patterns, msg.address_n)
            keychain = await get_keychain(ctx, CURVE, schemas)
            with keychain:
                return await func(ctx, msg, keychain)

        return wrapper

    return decorator


def _schemas_from_chain_id(msg: EthereumSignTx) -> Iterable[paths.PathSchema]:
    if msg.chain_id is None:
        return _schemas_from_address_n(PATTERNS_ADDRESS, msg.address_n)

    info = networks.by_chain_id(msg.chain_id)
    if info is None:
        return ()

    slip44_id = info.slip44
    if networks.is_wanchain(msg.chain_id, msg.tx_type):
        slip44_id = networks.SLIP44_WANCHAIN
    return (paths.PathSchema(pattern, slip44_id) for pattern in PATTERNS_ADDRESS)


def with_keychain_from_chain_id(
    func: HandlerWithKeychain[EthereumSignTx, MsgOut]
) -> Handler[EthereumSignTx, MsgOut]:
    # this is only for SignTx, and only PATTERN_ADDRESS is allowed
    async def wrapper(ctx: wire.Context, msg: EthereumSignTx) -> MsgOut:
        schemas = _schemas_from_chain_id(msg)
        keychain = await get_keychain(ctx, CURVE, schemas)
        with keychain:
            return await func(ctx, msg, keychain)

    return wrapper
