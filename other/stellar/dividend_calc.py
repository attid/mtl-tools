# other/stellar/dividend_calc.py
"""Dividend calculation logic for EURMTL, SATSMTL, USDM."""

from typing import Optional
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass

from stellar_sdk import Asset

from other.config_reader import config
from other.web_tools import http_session_manager
from .constants import MTLAddresses, MTLAssets
from .balance_utils import stellar_get_holders


@dataclass
class DividendPayment:
    """Single dividend payment record."""
    address: str
    amount: Decimal
    asset: Asset


@dataclass
class DividendCalculation:
    """Result of dividend calculation."""
    payments: list[DividendPayment]
    total_amount: Decimal
    holder_count: int
    asset: Asset


async def get_bim_list_from_gsheet(agcm) -> list[list]:
    """
    Get BIM (Basic Income MTL) register participants from Google Sheets.

    Args:
        agcm: Authorized gspread client manager

    Returns:
        List of [address, has_eurmtl] pairs
    """
    agc = await agcm.authorize()
    ss = await agc.open("MTL_BIM_register")
    wks = await ss.worksheet("List")

    addresses = []
    data = await wks.get_all_values()
    for record in data[2:]:
        # Check column conditions for valid participant
        if record[20] and len(record[4]) == 56 and record[10] == 'TRUE':
            try:
                weight = float(record[17].replace(',', '.')) if record[17] else 0
                if weight > 0.5:
                    addresses.append(record[4])
            except (ValueError, IndexError):
                continue

    # Check EURMTL trustline for each address
    result = []
    for address in addresses:
        balances = {}
        try:
            response = await http_session_manager.get_web_request(
                'GET',
                url=f'{config.horizon_url}/accounts/{address}',
                return_type='json'
            )
            rq = response.data if isinstance(response.data, dict) else {}
            if rq.get("balances"):
                for balance in rq["balances"]:
                    if balance["asset_type"] == 'credit_alphanum12':
                        balances[balance["asset_code"]] = balance["balance"]
                has_eurmtl = 'EURMTL' in balances
                result.append([address, has_eurmtl])
        except Exception:
            result.append([address, False])

    return result


async def calculate_eurmtl_dividends(
    total_amount: Decimal,
    exclude_addresses: Optional[list[str]] = None,
) -> DividendCalculation:
    """
    Calculate EURMTL dividend distribution based on holder balances.

    Args:
        total_amount: Total amount to distribute
        exclude_addresses: Addresses to exclude from distribution

    Returns:
        DividendCalculation with payments list
    """
    exclude = set(exclude_addresses or [])
    exclude.add(MTLAddresses.public_issuer)
    exclude.add(MTLAddresses.public_div)

    # Get all EURMTL holders
    holders = await stellar_get_holders(MTLAssets.eurmtl_asset)

    # Calculate balances for eligible holders
    eligible_holders = []
    for holder in holders:
        address = holder["account_id"]
        if address in exclude:
            continue

        for balance in holder.get("balances", []):
            if (balance.get("asset_code") == "EURMTL" and
                balance.get("asset_issuer") == MTLAddresses.public_issuer):
                bal = Decimal(balance["balance"])
                if bal > Decimal("0"):
                    eligible_holders.append({
                        "address": address,
                        "balance": bal,
                    })
                break

    total_balance = sum(h["balance"] for h in eligible_holders)

    if total_balance == Decimal("0"):
        return DividendCalculation(
            payments=[],
            total_amount=Decimal("0"),
            holder_count=0,
            asset=MTLAssets.eurmtl_asset,
        )

    # Calculate per-holder payments
    payments = []
    for holder in eligible_holders:
        share = holder["balance"] / total_balance
        payment_amount = (total_amount * share).quantize(
            Decimal("0.0000001"),
            rounding=ROUND_DOWN
        )

        if payment_amount > Decimal("0"):
            payments.append(DividendPayment(
                address=holder["address"],
                amount=payment_amount,
                asset=MTLAssets.eurmtl_asset,
            ))

    return DividendCalculation(
        payments=payments,
        total_amount=sum(p.amount for p in payments),
        holder_count=len(payments),
        asset=MTLAssets.eurmtl_asset,
    )


async def calculate_mtlap_dividends(
    total_amount: Decimal,
    mtlap_holders: list[dict],
) -> DividendCalculation:
    """
    Calculate MTLAP holder dividend allocations.

    Args:
        total_amount: Total amount to distribute
        mtlap_holders: List of {address, balance} dicts

    Returns:
        DividendCalculation with payments list
    """
    total_weight = sum(Decimal(str(h.get("balance", 0))) for h in mtlap_holders)

    if total_weight == Decimal("0"):
        return DividendCalculation(
            payments=[],
            total_amount=Decimal("0"),
            holder_count=0,
            asset=MTLAssets.eurmtl_asset,
        )

    payments = []
    for holder in mtlap_holders:
        weight = Decimal(str(holder.get("balance", 0)))
        if weight <= Decimal("0"):
            continue

        share = weight / total_weight
        payment_amount = (total_amount * share).quantize(
            Decimal("0.0000001"),
            rounding=ROUND_DOWN
        )

        if payment_amount > Decimal("0"):
            payments.append(DividendPayment(
                address=holder["address"],
                amount=payment_amount,
                asset=MTLAssets.eurmtl_asset,
            ))

    return DividendCalculation(
        payments=payments,
        total_amount=sum(p.amount for p in payments),
        holder_count=len(payments),
        asset=MTLAssets.eurmtl_asset,
    )
