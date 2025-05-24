from flask import Flask, jsonify
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import time
import os
import io
import base64
import json

app = Flask(__name__)

def plot_last_patient_centile(patient_df, boys_centile_df, girls_centile_df):
    required_cols = ["Fetal Sex (Male, Female or Unknown)", "Birthweight (grams)", "Gestation (days)"]
    filtered_df = patient_df.dropna(subset=required_cols)

    for col in required_cols:
        filtered_df = filtered_df[filtered_df[col].astype(str).str.strip() != ""]

    if filtered_df.empty:
        return None

    last_row = filtered_df.iloc[-1]
    gender = str(last_row["Fetal Sex (Male, Female or Unknown)"]).strip().capitalize()

    if gender == "Male":
        centile_df = boys_centile_df
        line_style = "dashed"
    elif gender == "Female":
        centile_df = girls_centile_df
        line_style = "solid"
    else:
        return None

    plt.figure(figsize=(10, 6))
    palette = sns.color_palette("husl", len(centile_df.columns) - 1)

    for idx, col in enumerate(centile_df.columns[1:]):
        plt.plot(
            centile_df["Gestational Age"], centile_df[col],
            label=f'{col} Percentile',
            linestyle=line_style,
            color=palette[idx],
            alpha=0.6
        )

    plt.scatter(
        last_row["Gestation (days)"] / 7,
        last_row["Birthweight (grams)"],
        color="black",
        s=120,
        edgecolors='white',
        linewidth=2,
        zorder=3,
        label=f"{gender} Birthweight"
    )

    plt.title(f"{gender}'s Birthweight vs. Gestational Age", fontsize=14)
    plt.xlabel("Gestational Age (weeks)", fontsize=12)
    plt.ylabel("Birthweight (grams)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return image_base64

@app.route("/generate-plot", methods=["POST"])
def handle_plot_request():
    try:
        time.sleep(1)

        creds_info = json.loads(os.environ["GOOGLE_CREDS"])
        creds = Credentials.from_service_account_info(creds_info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        gc = gspread.authorize(creds)

        SHEET_ID = "1sVoCG-ikThXfEPlhmaJpqRaZiFoI8rAebiUSTYmbKGI"
        sh = gc.open_by_key(SHEET_ID)
        calculator = sh.worksheet("Calculator")  
        boys_centile_sheet = sh.worksheet("Boy's Centile")  
        girls_centile_sheet = sh.worksheet("Girl's Centile")

        boys_centile_df = pd.DataFrame(boys_centile_sheet.get_all_records())
        girls_centile_df = pd.DataFrame(girls_centile_sheet.get_all_records())
        patient_df = pd.DataFrame(calculator.get_all_records())
        sns.set_theme(style="whitegrid")

        image_base64 = plot_last_patient_centile(patient_df, boys_centile_df, girls_centile_df)
        if image_base64:
            return jsonify({ "image_base64": image_base64 })
        else:
            return jsonify({ "error": "Plot generation failed" }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({ "error": str(e) }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
