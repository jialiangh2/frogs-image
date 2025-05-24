from flask import Flask, jsonify
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import time
import requests
import os
app = Flask(__name__)

def plot_last_patient_centile(patient_df, boys_centile_df, girls_centile_df):
    required_cols = ["Fetal Sex (Male, Female or Unknown)", "Birthweight (grams)", "Gestation (days)"]
    filtered_df = patient_df.dropna(subset=required_cols)

    for col in required_cols:
        filtered_df = filtered_df[filtered_df[col].astype(str).str.strip() != ""]

    if filtered_df.empty:
        print("No valid data available.")
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
        print(f"Unsupported gender: {gender}")
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

    filename = f"plot_{int(time.time())}.png"
    plt.savefig(filename, bbox_inches='tight')
    print("Plot saved:", filename)

    headers = {
        "Authorization": "Client-ID a423b4dd7a62263"
    }

    with open(filename, "rb") as img:
        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            files={"image": img}
        )

    if response.status_code == 200:
        image_url = response.json()["data"]["link"]
        print("✅ Imgur upload complete:", image_url)
        return image_url
    else:
        print("❌ Upload failed:", response.text)
        return None

@app.route("/generate-plot", methods=["POST"])
def handle_plot_request():
    time.sleep(1)  # Allow time for Sheets to update

    creds = Credentials.from_service_account_file("credentials.json", scopes=[
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

    image_url = plot_last_patient_centile(patient_df, boys_centile_df, girls_centile_df)
    if image_url:
        return jsonify({ "image_url": image_url })
    else:
        return jsonify({ "error": "Plot generation or upload failed" }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
