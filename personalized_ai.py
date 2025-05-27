import streamlit as st
import chromadb  # vector memory ko save karny or aik jaisy notes search karny ky liye
import json
import os
from datetime import datetime
import google.generativeai as genai
import time # time ko note karny ky liye ky kitna time lagy ga action main
import random #random note ko uthany ky liye hy
import re # tags aur question ko extract karny ky liye
import concurrent.futures # time out karny ky liye agar koi function zyada time le raha ho

GEMINI_API_KEY ="AIzaSyCv86uC98jkzdzO6eCR4Tjav1AcGxIT2gQ"  
MEMORY_FILE ="user_memory.json"


genai.configure(api_key=GEMINI_API_KEY)
llm = genai.GenerativeModel("gemini-2.0-flash")


chroma_client = chromadb.Client()
try:
    collection = chroma_client.get_collection("memory")
except Exception:
    collection =chroma_client.create_collection("memory")


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE,"r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)


st.title("AI Memory Companion")

tab = st.sidebar.selectbox("Choose Feature", [
    "Add Note",
    "Recall Memory",
    "Daily Summary",
    "Revise Past Content",
    "Auto-Tag & Question Gen",
    "Clear All Memory"
])


if tab == "Add Note":
    note = st.text_area("Write your thought, notes, or learning")
    if st.button("Save Note"):
        start = time.time()
        mem = load_memory()
        timestamp = datetime.now().isoformat()
        mem.append({"note": note, "timestamp": timestamp})
        save_memory(mem)
        st.success("Note saved to memory!")  


        collection.add(
            documents=[note],
            metadatas=[{"timestamp": timestamp}],
            ids=[timestamp]
        )

elif tab == "Recall Memory":
    query = st.text_input("What do you want to recall?")
    if st.button("Search Memory"):
        def do_query():
            return collection.query(query_texts=[query], n_results=3)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(do_query)
            try:
                results = future.result(timeout=30)
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                if docs:
                    st.subheader("Closest Memories:")
                    for doc, meta in zip(docs, metas):
                        st.write(f"- {doc} ({meta['timestamp']})")
                else:
                    st.warning("No relevant memories found.")
            except concurrent.futures.TimeoutError:
                st.error("Memory search took too long .Your device may not support this function.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

    
elif tab == "Daily Summary":
    mem = load_memory()
    today = datetime.now().date().isoformat()
    today_notes = [m["note"] for m in mem if m["timestamp"].startswith(today)]
    if today_notes:
        prompt = (
            f"Summarize these personal notes for today in a friendly way:\n\n" +
            "\n".join(today_notes)
        )
        if st.button("Generate Summary"):
            response = llm.generate_content(prompt)
            st.subheader("Today's Summary")
            st.write(response.text.strip())
    else:
        st.info("No notes found for today.")

elif tab == "Revise Past Content":
    mem = load_memory()
    if mem:
        note = random.choice(mem)["note"]
        st.write(f"Revise this note: {note}")
        if st.button("Explanation"):
            prompt = f"Explain this note simply: {note}"
            response = llm.generate_content(prompt)
            st.write(response.text.strip())
    else:
        st.info("No notes to revise.")

elif tab == "Auto-Tag & Question Gen":
    mem = load_memory()
    if mem:
        note =st.selectbox("Select a note",[m["note"] for m in mem])
        if st.button("Auto-Tag & Generate Question"):
            prompt = (
                f"Auto-tag this note with 3 relevant tags and generate a quiz question for revision. "
                f"Format your response as:\n"
                f"Tags: <tag1>, <tag2>, <tag3>\n"
                f"Question: <quiz question>\n"
                f"Options:\nA) <option1>\nB) <option2>\nC) <option3>\nD) <option4>\n"
                f"Answer: <correct option letter>\n"
                f"\nNote:\n{note}"
            )
            response =llm.generate_content(prompt)
            output =response.text.strip()

           
            tags = re.search(r"Tags:\s*(.*)", output)
            question = re.search(r"Question:\s*(.*)",output)
            options = re.findall(r"[A-D]\)\s*(.*)",output)
            answer = re.search(r"Answer:\s*([A-D])", output)

            if tags:
                st.markdown(f"**Tags:**{tags.group(1)}")
            if question:
                st.markdown(f"**Quiz Question:** {question.group(1)}")
            if options:
                st.markdown("**Options:**")
                for idx, opt in zip(['A','B','C','D'],options):
                    st.markdown(f"- {idx}) {opt}")
            if answer:
                st.markdown(f"**Correct Answer:** {answer.group(1)}")
            st.markdown("---")
    else:
        st.info("No notes found.")

elif tab =="Clear All Memory":
    if st.button("Clear All Memory"):
        save_memory([])
        all_ids = collection.get()['ids']
        if all_ids:
            collection.delete(ids=all_ids)
        st.success("All memory cleared!")