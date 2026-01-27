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
- asset_xdr: Asset-specific XDR generation (dividends, payments)
- monitoring: Transaction monitoring and detection
- xdr_utils: XDR decoding and transaction utilities
- voting_utils: Voting and governance utilities
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

# Asset-specific XDR generation
from .asset_xdr import (
    get_damircoin_xdr,
    get_agora_xdr,
    get_toc_xdr,
    get_btcmtl_xdr,
    get_chicago_xdr,
)

# Transaction monitoring
from .monitoring import (
    cmd_check_new_transaction,
    cmd_check_new_asset_transaction,
    cmd_check_last_operation,
    get_memo_by_op,
    stellar_get_transactions,
)

# XDR utilities
from .xdr_utils import (
    check_url_xdr,
    decode_xdr,
    cmd_check_fee,
    stellar_get_transaction_builder,
    decode_data_value,
)

# Voting and governance
from .voting_utils import (
    cmd_get_new_vote_all_mtl,
    get_mtlap_votes,
    cmd_gen_mtl_vote_list,
    cmd_gen_fin_vote_list,
    gen_vote_xdr,
    cmd_get_blacklist,
    check_mtla_delegate,
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
    # Asset XDR
    "get_damircoin_xdr",
    "get_agora_xdr",
    "get_toc_xdr",
    "get_btcmtl_xdr",
    "get_chicago_xdr",
    # Monitoring
    "cmd_check_new_transaction",
    "cmd_check_new_asset_transaction",
    "cmd_check_last_operation",
    "get_memo_by_op",
    "stellar_get_transactions",
    # XDR utilities
    "check_url_xdr",
    "decode_xdr",
    "cmd_check_fee",
    "stellar_get_transaction_builder",
    "decode_data_value",
    # Voting and governance
    "cmd_get_new_vote_all_mtl",
    "get_mtlap_votes",
    "cmd_gen_mtl_vote_list",
    "cmd_gen_fin_vote_list",
    "gen_vote_xdr",
    "cmd_get_blacklist",
    "check_mtla_delegate",
]
