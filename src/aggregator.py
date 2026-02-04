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

    # Sort logic: Make sure "Total" is at the bottom if possible, or keep original order
    # For now, let's sort by Sales descending just to have order, or rely on original PDF order?
    # Keeping it simple for now. 
    # If "総合計" (Grand Total) is present, move it to the end.
    
    # Identify Grand Total row
    total_row_mask = summary['Zone'] == '【総合計】'
    if total_row_mask.any():
        total_row = summary[total_row_mask]
        others = summary[~total_row_mask]
        summary = pd.concat([others, total_row])

    return summary
