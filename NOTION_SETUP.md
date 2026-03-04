# Notion Integration Setup Guide

## Step 1: Create a Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it: "Teacher Attendance Tracker"
4. Select your workspace
5. Click "Submit"
6. **Copy the "Internal Integration Token"** (starts with `secret_...`)

## Step 2: Get Your Database ID

1. Open your Teachers database in Notion
2. Click "Share" in the top right
3. Click "Copy link"
4. The link looks like: `https://notion.so/workspace/DATABASE_ID?v=...`
5. **Copy the DATABASE_ID** (the long string of letters/numbers before the `?`)

Alternative method:
- Open database as a full page
- Look at URL: `https://notion.so/DATABASE_ID`
- Copy the 32-character ID

## Step 3: Share Database with Integration

1. Open your Teachers database in Notion
2. Click the "..." menu (top right)
3. Scroll down to "Connections"
4. Click "+ Add connection"
5. Select "Teacher Attendance Tracker" (your integration)
6. Click "Confirm"

## Step 4: Configure Your App

1. In your project folder, create a file named `.env`:

```bash
cd /Users/edward/face-attendance-app
touch .env
```

2. Edit `.env` and add:

```
NOTION_API_KEY=secret_YOUR_KEY_HERE
NOTION_DATABASE_ID=YOUR_DATABASE_ID_HERE
```

Replace with your actual values from Steps 1 and 2.

## Step 5: Required Database Properties

Your Notion database should have these properties:

**Required:**
- `Name` (Title) - Teacher's name
- `Last Attendance` (Date) - Auto-updated on check-in
- `Total Check-ins` (Number) - Counter
- `Status` (Select) - Present/Absent

**Optional:**
- `Email` (Email)
- `Department` (Select)
- `Notes` (Text)

The app will automatically:
- Update "Last Attendance" when they check in
- Increment "Total Check-ins" counter
- Set "Status" to "Present"

## Step 6: Install Dependencies

```bash
/usr/local/bin/python3.11 -m pip install notion-client python-dotenv
```

Or from requirements.txt:
```bash
/usr/local/bin/python3.11 -m pip install -r requirements.txt
```

## Step 7: Restart Server

```bash
# Stop current server (Ctrl+C if running in terminal)
# Or kill the process

# Start with new Notion integration
/usr/local/bin/python3.11 server.py
```

## Testing

1. Open your app in browser
2. Go to Register tab
3. You should see a dropdown with teachers from Notion
4. Register face → Linked to Notion entry
5. Check in → Updates Notion database automatically

## Troubleshooting

**"Integration not found"**
- Make sure you shared the database with your integration (Step 3)

**"Database not found"**
- Check DATABASE_ID is correct
- Make sure integration has access

**"Unauthorized"**
- Verify API_KEY starts with `secret_`
- Check for typos in .env file

**No teachers showing up**
- Ensure database has a "Name" property (Title type)
- Check database is not empty

## Security

⚠️ **Never commit `.env` file to git!**

The `.env` file contains secrets. It's already in `.gitignore`.
