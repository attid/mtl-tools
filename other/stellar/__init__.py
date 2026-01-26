# other/stellar/__init__.py
"""
Stellar blockchain utilities for MTL ecosystem.

This module provides a clean interface to Stellar operations,
organized by responsibility:

- constants: MTL addresses, assets, configuration
- sdk_utils: Low-level SDK operations (keypair, signing, server)
- address_utils: Address resolution and federation
- balance_utils: Balance queries and account info
- payment_service: Payment operations and submissions
- dividend_calc: Dividend calculation logic
- exchange_utils: Exchange operations and swaps
"""

# Constants
from .constants import (
    BASE_FEE,
    PACK_COUNT,
    MTLAddresses,
    MTLAssets,
    EXCHANGE_BOTS,
)

# SDK utilities
from .sdk_utils import (
    get_server,
    get_server_async,
    get_private_sign,
    stellar_sign,
    gen_new,
    decode_xdr_envelope,
)

# Address utilities
from .address_utils import (
    find_stellar_public_key,
    find_stellar_federation_address,
    resolve_account,
    address_id_to_username,
    shorten_address,
)

# Balance utilities
from .balance_utils import (
    stellar_get_account,
    get_balances,
    stellar_get_issuer_assets,
    stellar_get_holders,
    stellar_get_token_amount,
    stellar_get_all_mtl_holders,
)

# Payment operations
from .payment_service import (
    send_payment_async,
    stellar_async_submit,
    stellar_sync_submit,
    build_batch_payment_xdr,
)

# Dividend calculations
from .dividend_calc import (
    DividendPayment,
    DividendCalculation,
    get_bim_list_from_gsheet,
    calculate_eurmtl_dividends,
    calculate_mtlap_dividends,
)

# Exchange utilities
from .exchange_utils import (
    stellar_get_offers,
    stellar_get_orders_sum,
    get_asset_swap_spread,
    stellar_get_receive_path,
    build_swap_xdr,
    build_cancel_offers_xdr,
)


__all__ = [
    # Constants
    "BASE_FEE",
    "PACK_COUNT",
    "MTLAddresses",
    "MTLAssets",
    "EXCHANGE_BOTS",
    # SDK
    "get_server",
    "get_server_async",
    "get_private_sign",
    "stellar_sign",
    "gen_new",
    "decode_xdr_envelope",
    # Address
    "find_stellar_public_key",
    "find_stellar_federation_address",
    "resolve_account",
    "address_id_to_username",
    "shorten_address",
    # Balance
    "stellar_get_account",
    "get_balances",
    "stellar_get_issuer_assets",
    "stellar_get_holders",
    "stellar_get_token_amount",
    "stellar_get_all_mtl_holders",
    # Payment
    "send_payment_async",
    "stellar_async_submit",
    "stellar_sync_submit",
    "build_batch_payment_xdr",
    # Dividend
    "DividendPayment",
    "DividendCalculation",
    "get_bim_list_from_gsheet",
    "calculate_eurmtl_dividends",
    "calculate_mtlap_dividends",
    # Exchange
    "stellar_get_offers",
    "stellar_get_orders_sum",
    "get_asset_swap_spread",
    "stellar_get_receive_path",
    "build_swap_xdr",
    "build_cancel_offers_xdr",
]
