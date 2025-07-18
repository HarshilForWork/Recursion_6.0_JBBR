# Recursion_6.0_JBBR

## Project Structure (Optimized)

```
Recursion_6.0_JBBR/
│
├── backend/
│   ├── app.py
│   ├── routes.py
│   ├── model/
│   │   └── (all model files)
│   └── requirements.txt
│
├── frontend/
│   ├── static/
│   │   ├── assets/
│   │   └── styles/
│   ├── templates/
│   └── (all frontend files)
│
├── run_all.py  # Script to start both backend and frontend
├── README.md
```

## Usage

1. **Install dependencies:**
   - Backend: `cd backend && pip install -r requirements.txt`

2. **Run the project:**
   - From the root directory, run: `python run_all.py`
   - This will start both backend and frontend servers.

3. **Access the app:**
   - Open your browser at `http://localhost:5000` (or the port specified in the script).

## Features
- Pressing the Generate button on the frontend triggers the model in the backend and displays the output.
- Clean, maintainable directory structure.