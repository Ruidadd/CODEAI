"""
Export utilities for business card data
"""
import json
import pandas as pd
from io import BytesIO
from typing import List
from card_recognizer import BusinessCardInfo


def cards_to_dataframe(cards: List[BusinessCardInfo]) -> pd.DataFrame:
    """
    Convert a list of BusinessCardInfo objects to a pandas DataFrame

    Args:
        cards: List of BusinessCardInfo objects

    Returns:
        pandas DataFrame with all card information
    """
    data = [card.to_dict() for card in cards]
    df = pd.DataFrame(data)

    # Rename columns for better readability
    column_names = {
        "name": "姓名 / Name",
        "company": "公司 / Company",
        "title": "职位 / Title",
        "email": "邮箱 / Email",
        "phone": "电话 / Phone",
        "mobile": "手机 / Mobile",
        "fax": "传真 / Fax",
        "address": "地址 / Address",
        "website": "网站 / Website",
        "linkedin": "LinkedIn",
        "wechat": "微信 / WeChat",
        "notes": "备注 / Notes"
    }
    df = df.rename(columns=column_names)

    return df


def export_to_csv(cards: List[BusinessCardInfo]) -> str:
    """
    Export cards to CSV format

    Args:
        cards: List of BusinessCardInfo objects

    Returns:
        CSV string
    """
    df = cards_to_dataframe(cards)
    return df.to_csv(index=False, encoding="utf-8-sig")


def export_to_excel(cards: List[BusinessCardInfo]) -> BytesIO:
    """
    Export cards to Excel format

    Args:
        cards: List of BusinessCardInfo objects

    Returns:
        BytesIO object containing the Excel file
    """
    df = cards_to_dataframe(cards)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Business Cards")

        # Auto-adjust column widths
        worksheet = writer.sheets["Business Cards"]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            # Limit column width
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width

    output.seek(0)
    return output


def export_to_json(cards: List[BusinessCardInfo], pretty: bool = True) -> str:
    """
    Export cards to JSON format

    Args:
        cards: List of BusinessCardInfo objects
        pretty: Whether to format the JSON with indentation

    Returns:
        JSON string
    """
    data = [card.to_dict() for card in cards]
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False)


def export_to_vcard(cards: List[BusinessCardInfo]) -> str:
    """
    Export cards to vCard format (.vcf)

    Args:
        cards: List of BusinessCardInfo objects

    Returns:
        vCard string
    """
    vcards = []

    for card in cards:
        vcard_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
        ]

        if card.name:
            vcard_lines.append(f"FN:{card.name}")
            # Try to split name into parts
            parts = card.name.split()
            if len(parts) >= 2:
                vcard_lines.append(f"N:{parts[-1]};{' '.join(parts[:-1])};;;")
            else:
                vcard_lines.append(f"N:{card.name};;;;")

        if card.company:
            vcard_lines.append(f"ORG:{card.company}")

        if card.title:
            vcard_lines.append(f"TITLE:{card.title}")

        if card.email:
            vcard_lines.append(f"EMAIL;TYPE=WORK:{card.email}")

        if card.phone:
            vcard_lines.append(f"TEL;TYPE=WORK,VOICE:{card.phone}")

        if card.mobile:
            vcard_lines.append(f"TEL;TYPE=CELL:{card.mobile}")

        if card.fax:
            vcard_lines.append(f"TEL;TYPE=FAX:{card.fax}")

        if card.address:
            # Escape special characters
            addr = card.address.replace(",", "\\,").replace(";", "\\;")
            vcard_lines.append(f"ADR;TYPE=WORK:;;{addr};;;;")

        if card.website:
            vcard_lines.append(f"URL:{card.website}")

        if card.linkedin:
            vcard_lines.append(f"X-SOCIALPROFILE;TYPE=linkedin:{card.linkedin}")

        if card.notes:
            notes = card.notes.replace("\n", "\\n")
            vcard_lines.append(f"NOTE:{notes}")

        vcard_lines.append("END:VCARD")
        vcards.append("\n".join(vcard_lines))

    return "\n\n".join(vcards)
