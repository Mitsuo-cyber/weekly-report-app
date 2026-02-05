import pandas as pd

def calculate_weekly_summary(daily_df):
    if daily_df.empty:
        return pd.DataFrame()

    # Calculate Last Year's Numbers to compute accurate Weighted YoY
    # Last Year Sales = Sales / (YoY / 100)
    # Handle division by zero or empty YoY
    
    def get_last_year(current, yoy):
        if yoy == 0:
            return 0
        return current / (yoy / 100)

    daily_df['Last_Year_Sales'] = daily_df.apply(lambda x: get_last_year(x['Sales'], x['Sales_YoY']), axis=1)
    daily_df['Last_Year_Count'] = daily_df.apply(lambda x: get_last_year(x['Count'], x['Count_YoY']), axis=1)

    # Group by Zone
    # We want to sum Sales, Last_Year_Sales, Count, Last_Year_Count
    grouped = daily_df.groupby('Zone')[['Sales', 'Last_Year_Sales', 'Count', 'Last_Year_Count']].sum()

    # Recalculate YoY
    grouped['Sales_YoY'] = (grouped['Sales'] / grouped['Last_Year_Sales'] * 100).fillna(0).round(1)
    grouped['Count_YoY'] = (grouped['Count'] / grouped['Last_Year_Count'] * 100).fillna(0).round(1)

    # Select final columns
    summary = grouped[['Sales', 'Sales_YoY', 'Count', 'Count_YoY']].reset_index()

    # Sort logic:
    # 1. Remove "【総合計】" (Grand Total) if present, as it is confusing/redundant with PSP Total
    summary = summary[~summary['Zone'].str.contains('総合計', na=False)]

    # 2. Ensure "【軽井沢PSP計】" (PSP Total) is at the top
    # Identify PSP Total row
    psp_mask = summary['Zone'].str.contains('PSP', na=False) & summary['Zone'].str.contains('計', na=False)
    
    if psp_mask.any():
        psp_row = summary[psp_mask]
        others = summary[~psp_mask].sort_values('Sales', ascending=False)
        summary = pd.concat([psp_row, others])
    else:
        summary = summary.sort_values('Sales', ascending=False)

    return summary
