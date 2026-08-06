import pandas as pd


def calculate_csat_from_excel(input_file_path, output_file_path, columns=None):
  """Calculates CSAT percentage for specified or all numeric columns in an Excel file

  and saves the results to a new Excel file.
  """
  # 1. Read the Excel file
  df = pd.read_excel(input_file_path)

  # If no specific columns are listed, automatically select all numeric columns
  if columns is None:
    columns = df.select_dtypes(include=["number"]).columns.tolist()

  results = []

  # 2. Iterate through each column to calculate CSAT
  for col in columns:
    # Drop missing/NaN values to get valid responses only
    valid_responses = df[col].dropna()
    total_valid = len(valid_responses)

    if total_valid > 0:
      # Count how many scores are 4 or 5
      positive_count = len(
          valid_responses[(valid_responses == 4) | (valid_responses == 5)]
      )

      # Calculate CSAT percentage
      csat_percentage = (positive_count / total_valid) * 100
    else:
      positive_count = 0
      csat_percentage = 0.0

    # Store the results
    results.append({
        "Column Name": col,
        "Total Responses": total_valid,
        "Positive Responses (4 & 5)": positive_count,
        "CSAT (%)": round(csat_percentage, 2),
    })

  # 3. Convert results into a new DataFrame
  csat_df = pd.DataFrame(results)

  # 4. Save the results to a new Excel file
  csat_df.to_excel(output_file_path, index=False)
  print(f"CSAT results successfully saved to: {output_file_path}")

  return csat_df


# --- Example Usage ---
# Replace 'survey_data.xlsx' with your actual input file name
# Replace 'csat_output.xlsx' with your desired output file name
input_file = "بيانات_استبيان_توكلنا_أفراد_Q2_2026م.xlsx"
output_file = "csat_output.xlsx"

# Optional: If you only want specific columns, list them like this:
# target_columns = ['Question_1', 'Question_2', 'Question_3']
# calculate_csat_from_excel(input_file, output_file, columns=target_columns)

# Or run it for all numeric columns automatically:
calculate_csat_from_excel(input_file, output_file)