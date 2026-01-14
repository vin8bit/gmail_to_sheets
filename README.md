# 📧 Gmail to Google Sheets Automation

This Python project automatically reads **unread emails** from your Gmail inbox and logs them into a **Google Sheets** spreadsheet for easy tracking and analysis.

---

## 📂 File Structure

<img width="325" height="353" alt="Project File Structure" src="https://github.com/user-attachments/assets/b07c5fc3-a4bd-40e7-8fea-3b709807288d" />

---

## 🚀 Features

- Reads unread emails from Gmail inbox
- Extracts the following email details:
  - Sender
  - Subject
  - Timestamp
  - Email body
- Supports **email filtering**:
  - Sender
  - Subject
  - Keywords
- Converts **HTML email content to plain text** for clean storage
- Appends extracted data to Google Sheets
- Tracks processed emails to avoid **duplicate entries**

---

## 🛠 Requirements

- Python **3.9 or above**
- Google Cloud Account
- Gmail Account

---

## ⚙️ Setup Guide

### Step 1: Enable Gmail API & Google Sheets API

1. Go to **Google Cloud Console**
2. Open the search bar
3. Search for **Gmail API** → Enable it
4. Search for **Google Sheets API** → Enable it

---

### Step 2: Configure OAuth Consent Screen

1. Open **☰ Menu → APIs & Services → OAuth Consent Screen**
2. Click **Configure Consent Screen**
3. Select **External** user type
4. Fill required details:
   - **App name**: Gmail to Sheets Automation
   - **User support email**: Your email
   - **Developer contact email**: Your email
5. Click **Save and Continue**
6. Complete the setup and finish

---

### Step 3: Create OAuth Client ID (Credentials)

1. Go to **☰ Menu → APIs & Services → OAuth Consent Screen → Clients**
2. Click **Create Client**
3. Choose **Application type**: Desktop App
4. Name it: `Gmail Email Logs`
5. Click **Create**
6. Download the credentials JSON file
7. Rename it to `credentials.json`
8. Place it inside the project root directory

---

### Step 4: Add Yourself as a Test User

1. Go to **☰ Menu → APIs & Services → OAuth Consent Screen → Audience**
2. Scroll to **Test Users**
3. Click **ADD USERS**
4. Add your Gmail address
5. Click **SAVE**

---

### Step 5: Publish the App

1. Click **PUBLISH APP**
2. Click **CONFIRM**
3. Wait **2–5 minutes** for changes to propagate

---

## ▶️ Running the Project

### Installation

```bash
pip install -r requirements.txt





