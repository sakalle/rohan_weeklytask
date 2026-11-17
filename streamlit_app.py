import json
import os

import requests
import streamlit as st

API_URL = os.getenv("FLASK_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
API_KEY = os.getenv("TICKET_API_KEY", "dev-key-change-me")


def api_request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = API_KEY
    headers.setdefault("Content-Type", "application/json")
    try:
        response = requests.request(
            method, f"{API_URL}{path}", headers=headers, timeout=30, **kwargs
        )
        if response.status_code >= 400:
            try:
                message = response.json().get("message") or response.json().get("error")
            except ValueError:
                message = response.text
            raise RuntimeError(f"HTTP {response.status_code}: {message}")
        return response
    except requests.RequestException as error:
        raise RuntimeError(f"Could not reach Flask API: {error}") from error


def show_error(error: Exception) -> None:
    st.error(str(error))


def render_chat() -> None:
    st.header("Support chat")
    st.caption("Answers are grounded in the SupportDesk knowledge base.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.write(f"**{source['title']}** — {source['source']}")
                        st.caption(source["snippet"])

    question = st.chat_input("Ask a support question")
    if not question:
        if not st.session_state.messages:
            st.info("Ask a question to start the conversation.")
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        answer_placeholder = st.empty()
        sources = []
        answer = ""
        try:
            response = api_request(
                "POST",
                "/chat/stream",
                json={
                    "question": question,
                    "conversation_id": st.session_state.get("conversation_id"),
                },
                headers={"Accept": "text/event-stream"},
            )
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event["type"] == "sources":
                    sources = event["sources"]
                elif event["type"] == "answer":
                    answer = event["answer"]
                    answer_placeholder.markdown(answer)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "sources": sources}
            )
            if sources:
                with st.expander("Sources"):
                    for source in sources:
                        st.write(f"**{source['title']}** — {source['source']}")
                        st.caption(source["snippet"])
        except (RuntimeError, ValueError, KeyError) as error:
            show_error(error)


def render_tickets() -> None:
    st.header("Tickets")
    try:
        response = api_request("GET", "/tickets")
        tickets = response.json().get("items", [])
    except (RuntimeError, ValueError) as error:
        show_error(error)
        return
    if not tickets:
        st.info("No tickets have been created yet.")
    else:
        priority = st.selectbox("Filter by priority", ["all", "high", "low"])
        visible = [
            ticket for ticket in tickets if priority == "all" or ticket["priority"] == priority
        ]
        st.dataframe(visible, use_container_width=True, hide_index=True)
        for ticket in visible:
            with st.expander(f"Ticket #{ticket['id']}: {ticket['title']}"):
                if st.button("AI classify", key=f"classify-{ticket['id']}"):
                    try:
                        result = api_request(
                            "POST", "/ai/classify", json={"text": ticket["description"]}
                        ).json()
                        st.json(result)
                    except (RuntimeError, ValueError) as error:
                        show_error(error)
                status = st.selectbox(
                    "Status",
                    ["open", "in_progress", "resolved"],
                    index=["open", "in_progress", "resolved"].index(ticket["status"])
                    if ticket["status"] in ["open", "in_progress", "resolved"]
                    else 0,
                    key=f"status-{ticket['id']}",
                )
                if st.button("Update status", key=f"update-{ticket['id']}"):
                    try:
                        api_request(
                            "PATCH",
                            f"/tickets/{ticket['id']}",
                            json={"status": status},
                        )
                        st.success("Ticket updated.")
                        st.rerun()
                    except RuntimeError as error:
                        show_error(error)

    with st.form("create-ticket"):
        st.subheader("Create ticket")
        title = st.text_input("Title")
        description = st.text_area("Description")
        email = st.text_input("Customer email")
        ticket_priority = st.selectbox("Priority", ["low", "high"])
        submitted = st.form_submit_button("Create ticket")
    if submitted:
        if not title or not description or not email:
            st.warning("Title, description, and email are required.")
        else:
            try:
                api_request(
                    "POST",
                    "/tickets",
                    json={
                        "title": title,
                        "description": description,
                        "customer_email": email,
                        "priority": ticket_priority,
                    },
                )
                st.success("Ticket created.")
                st.rerun()
            except RuntimeError as error:
                show_error(error)


def render_knowledge_base() -> None:
    st.header("Knowledge base")
    uploaded = st.file_uploader("Upload a text or Markdown document", type=["txt", "md"])
    title = st.text_input("Document title")
    source = st.text_input("Source", value="streamlit-upload")
    if st.button("Ingest document", disabled=uploaded is None):
        try:
            content = uploaded.getvalue().decode("utf-8")
            result = api_request(
                "POST",
                "/docs/ingest",
                json={"title": title or uploaded.name, "content": content, "source": source},
            ).json()
            st.success(f"Ingested document #{result['id']}.")
        except (RuntimeError, UnicodeDecodeError, ValueError) as error:
            show_error(error)
    try:
        documents = api_request("GET", "/knowledge").json()
        if not documents:
            st.info("No knowledge documents have been ingested yet.")
        else:
            st.dataframe(documents, use_container_width=True, hide_index=True)
    except (RuntimeError, ValueError) as error:
        show_error(error)


def render_dashboard() -> None:
    st.header("Dashboard")
    try:
        summary = api_request("GET", "/metrics/summary").json()
    except (RuntimeError, ValueError) as error:
        show_error(error)
        return
    if not summary["tickets"]["total"]:
        st.info("No ticket metrics are available yet.")
        return
    first, second, third = st.columns(3)
    first.metric("Tickets", summary["tickets"]["total"])
    second.metric("Average AI cost", f"${summary['ai_usage']['average_cost']:.6f}")
    third.metric("n8n configured", "Yes" if summary["n8n_configured"] else "No")
    st.subheader("Tickets by priority")
    st.bar_chart(summary["tickets"]["by_priority"])
    st.subheader("AI usage")
    st.json(summary["ai_usage"])


st.set_page_config(page_title="SupportDesk AI", page_icon="💬", layout="wide")
st.title("SupportDesk AI")
st.caption("Streamlit interface for the Flask + Groq + n8n support platform")
page = st.sidebar.radio("Navigate", ["Chat", "Tickets", "Knowledge base", "Dashboard"])

if page == "Chat":
    render_chat()
elif page == "Tickets":
    render_tickets()
elif page == "Knowledge base":
    render_knowledge_base()
else:
    render_dashboard()
