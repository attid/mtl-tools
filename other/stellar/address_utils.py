# other/stellar/address_utils.py
"""Address resolution, federation, and key extraction utilities."""

import re
from typing import Optional

from stellar_sdk.sep.federation import resolve_account_id_async


# Regex patterns
STELLAR_PUBLIC_KEY_PATTERN = re.compile(r'G[A-Za-z0-9]{55}')
STELLAR_FEDERATION_ADDRESS_PATTERN = re.compile(r'[a-z0-9]+[\._]?[a-z0-9]+[*][a-z0-9\-]+[\.][a-z0-9\.]+')


def find_stellar_public_key(text: str) -> Optional[str]:
    """
    Extract Stellar public key from text.

    Stellar public keys start with 'G' and contain 56 characters.

    Args:
        text: Text containing potential public key

    Returns:
        Public key string or None
    """
    match = STELLAR_PUBLIC_KEY_PATTERN.search(text)
    return match.group(0) if match else None


def find_stellar_federation_address(text: str) -> Optional[str]:
    """
    Extract Stellar federation address from text.

    Federation addresses have format 'username*domain.com'.

    Args:
        text: Text containing potential federation address

    Returns:
        Federation address string or None
    """
    match = STELLAR_FEDERATION_ADDRESS_PATTERN.search(text)
    return match.group(0) if match else None


async def resolve_account(address: str) -> Optional[str]:
    """
    Resolve federation address to account ID.

    Args:
        address: Federation address (e.g., user*domain.com)

    Returns:
        Stellar account ID or None if resolution fails
    """
    if not address or '*' not in address:
        return None

    try:
        result = await resolve_account_id_async(address)
        return result.account_id
    except Exception:
        return None


def shorten_address(address: str) -> str:
    """
    Return shortened version of Stellar address.

    Args:
        address: Full Stellar public key

    Returns:
        Shortened address like 'GABC..XY7V'
    """
    if not address or len(address) < 10:
        return address
    return f"{address[:4]}..{address[-4:]}"


async def address_id_to_username(
    key: str,
    full_data: bool = False,
    grist_manager=None,
    global_data=None
) -> str:
    """
    Convert Stellar address to human-readable username.

    Looks up address in Grist tables and global data to find username.

    Args:
        key: Stellar public key
        full_data: Whether to perform full lookup or just shorten
        grist_manager: Optional Grist manager for table lookups
        global_data: Optional global data for name list cache

    Returns:
        Username or shortened address if not found
    """
    if not key:
        return key

    if not full_data:
        return shorten_address(key)

    # Check global name list first (cache)
    if global_data and hasattr(global_data, 'name_list'):
        if key in global_data.name_list:
            return global_data.name_list[key]

    # Try Grist lookup if manager provided
    if grist_manager:
        try:
            # Check MTLA users
            from other.grist_tools import MTLGrist
            user = await grist_manager.load_table_data(
                MTLGrist.MTLA_USERS,
                filter_dict={"Stellar": [key]}
            )
            if user:
                name = user[0]["Telegram"]
                if global_data and hasattr(global_data, 'name_list'):
                    global_data.name_list[key] = name
                return name

            # Check EURMTL users
            user = await grist_manager.load_table_data(
                MTLGrist.EURMTL_users,
                filter_dict={"account_id": [key]}
            )
            if user:
                name = user[0]["username"]
                if global_data and hasattr(global_data, 'name_list'):
                    global_data.name_list[key] = name
                return name

            # Check EURMTL accounts
            user = await grist_manager.load_table_data(
                MTLGrist.EURMTL_accounts,
                filter_dict={"account_id": [key]}
            )
            if user:
                name = user[0]["description"]
                if global_data and hasattr(global_data, 'name_list'):
                    global_data.name_list[key] = name
                return name

            # Check EURMTL assets (issuer lookup)
            user = await grist_manager.load_table_data(
                MTLGrist.EURMTL_assets,
                filter_dict={"issuer": [key]}
            )
            if user:
                name = 'Issuer of ' + user[0]["code"]
                if global_data and hasattr(global_data, 'name_list'):
                    global_data.name_list[key] = name
                return name
        except Exception:
            pass

    # Return shortened address as fallback
    return f"{shorten_address(key)} не найден, возможно скам"
