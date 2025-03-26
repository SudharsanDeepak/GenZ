import streamlit as st
import webbrowser
import requests
import time
import os
import json
from collections import defaultdict, deque
import google.generativeai as genai
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import TimeoutException, WebDriverException

API_KEY = "AIzaSyAuqflDWBKYP3edhkTH69qoTKJZ_BgbNW8"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

st.title("🤖 HackerRank Auto-Solver & Analytics Chatbot (Gemini AI)")
st.write("Type Solve HackerRank [problem name] in any format or ask anything!")

@st.cache_data
def fetch_problems():
    return {}

problems_dict = fetch_problems()

st.session_state.setdefault("analytics", defaultdict(lambda: {"attempts": 0, "solutions": []}))
st.session_state.setdefault("problem_history", deque(maxlen=10))
st.session_state.setdefault("solved_problems", set())

def open_problem(problem_name, lang):
    url = f"https://www.hackerrank.com/challenges/{lang}/problem?isFullScreen=true"
    webbrowser.open(url)
    return url

def get_problem_statement(problem_name):
    try:
        url = f"https://www.hackerrank.com/challenges/{problem_name}/problem"
        res = requests.get(url)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            statement = soup.find("div", class_="challenge_problem_statement")
            return statement.get_text(strip=True) if statement else "❌ Problem statement not found."
    except Exception as e:
        return f"❌ Error fetching problem: {e}"
    return "❌ Failed to fetch problem."

def solve_with_gemini(problem_name, lang, text):
    if text.startswith("❌"): return "❌ Problem fetch failed."
    prompt = f"""Solve the following HackerRank problem in {lang}:
Problem:  
{text}
Requirements:
- Follow HackerRank function signature.
- Return only function implementation.
- Optimize for efficiency.
Solution:"""
    try:
        res = model.generate_content(prompt)
        sol = res.text.strip()
        st.session_state.analytics[problem_name]["solutions"].append(sol)
        st.session_state.analytics[problem_name]["attempts"] += 1
        return sol
    except Exception as e:
        return f"❌ Gemini Error: {e}"

def submit_solution_and_paste(problem_name, lang, sol):
    url = f"https://www.hackerrank.com/challenges/{problem_name}/problem"
    user_data_dir = r"C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Microsoft\\Edge\\User Data"
    profile = "Default"
    options = EdgeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile}")
    options.add_argument("--start-maximized")
    driver_path = r"C:\\WebDrivers\\msedgedriver.exe"
    if not os.path.exists(driver_path):
        st.error(f"❌ WebDriver not found: {driver_path}")
        return
    try:
        driver = webdriver.Edge(service=EdgeService(driver_path), options=options)
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "ace_editor")))
        time.sleep(2)
        escaped_sol = json.dumps(sol)
        inject_js = f"""
            var editor = ace.edit(document.querySelector('.ace_editor'));
            editor.setValue({escaped_sol});
        """
        driver.execute_script(inject_js)
        time.sleep(2)
        run_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Run Code')]")))
        run_btn.click()
        time.sleep(10)
        try:
            result = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "congrats-message")))
            if "Success" in result.text:
                st.success(f"✅ Problem {problem_name} solved!")
                st.session_state.solved_problems.add(problem_name)
            else:
                st.error("❌ Solution failed.")
        except TimeoutException:
            st.error("❌ Solution run failed.")
    except WebDriverException as e:
        st.error(f"❌ Selenium Error: {e}")
    finally:
        try: driver.quit()
        except: pass

user_input = st.text_input("Your command or question:")

if "hackerrank" in user_input.lower():
    tokens = user_input.lower().split()
    problem_name = next((t for t in tokens if "hackerrank" not in t), None)
    if problem_name:
        lang = st.selectbox("Language", ["python", "java", "cpp", "javascript", "csharp"])
        if st.button("Generate & Submit Solution"):
            st.session_state.problem_history.append(problem_name)
            open_problem(problem_name, lang)
            text = get_problem_statement(problem_name)
            solution = solve_with_gemini(problem_name, lang, text)
            st.code(solution, language=lang)
            submit_solution_and_paste(problem_name, lang, solution)
    else:
        st.error("❌ Provide a valid problem name.")
elif user_input:
    try:
        res = model.generate_content(user_input)
        st.chat_message("assistant").write(res.text)
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")

if st.button("Show Analytics"):
    st.write("### 📈 Problem Solving Analytics")
    for problem_name, data in st.session_state.analytics.items():
        st.write(f"Problem {problem_name}: Attempts: {data['attempts']}")
        for sol in data["solutions"]:
            st.code(sol, language="python")

if st.session_state.problem_history:
    st.write("### 🕘 Recent Problems:")
    for problem_name in reversed(st.session_state.problem_history):
        st.write(f"- Problem {problem_name}")
if st.session_state.solved_problems:
    st.write("### ✅ Solved:")
    st.write(", ".join(sorted(st.session_state.solved_problems)))