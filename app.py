# app.py
import streamlit as st
import json
from workflow_runner import run_customer_support_workflow

# Page config
st.set_page_config(page_title="Langie - Customer Support Agent", page_icon="🤖")

# Title
st.title("🤖 Langie - Customer Support Agent")
st.write("Hi, I am Langie, your customer support agent. How can I help you today?")

# Initialize session state
if 'workflow_state' not in st.session_state:
    st.session_state.workflow_state = None
if 'human_inputs' not in st.session_state:
    st.session_state.human_inputs = []
if 'workflow_started' not in st.session_state:
    st.session_state.workflow_started = False

# Input form
with st.form("customer_form"):
    st.subheader("📝 Enter Your Details")
    customer_name = st.text_input("Your Name:", placeholder="Enter your full name")
    email = st.text_input("Your Email:", placeholder="your.email@example.com")
    query = st.text_area("Describe your issue:", placeholder="Please describe your problem in detail...", height=100)
    
    submitted = st.form_submit_button("🚀 Start Support Request", use_container_width=True)

# Handle form submission
if submitted and customer_name and email and query:
    st.session_state.workflow_started = True
    st.session_state.human_inputs = []
    
    with st.spinner("🔄 Processing your request..."):
        result = run_customer_support_workflow(customer_name, email, query, st.session_state.human_inputs)
        st.session_state.workflow_state = result
    
    st.success("✅ Request processed!")

elif submitted:
    st.error("❌ Please fill in all fields.")

# Handle human input needed
if st.session_state.workflow_state and "_human_input_needed" in st.session_state.workflow_state:
    ability_needed = st.session_state.workflow_state["_human_input_needed"]
    
    st.divider()
    st.subheader("💬 Additional Information Needed")
    
    if ability_needed == "clarify_question":
        question = st.session_state.workflow_state.get("clarify_question", "Could you provide more details about your issue?")
        st.info(f"**Question:** {question}")
        
        with st.form("clarification_form"):
            user_answer = st.text_area("Your answer:", placeholder="Please provide the requested information...")
            if st.form_submit_button("Submit Answer"):
                st.session_state.human_inputs.append(user_answer)
                
                with st.spinner("🔄 Continuing workflow..."):
                    result = run_customer_support_workflow(
                        st.session_state.workflow_state["customer_name"],
                        st.session_state.workflow_state["email"],
                        st.session_state.workflow_state["query"],
                        st.session_state.human_inputs
                    )
                    st.session_state.workflow_state = result
                
                st.rerun()
    
    elif ability_needed == "extract_answer":
        clarify_question = st.session_state.workflow_state.get("clarify_question", "Please provide more details:")
        st.info(f"**Follow-up:** {clarify_question}")
        
        with st.form("answer_form"):
            user_answer = st.text_area("Your response:", placeholder="Your detailed response...")
            if st.form_submit_button("Submit Response"):
                st.session_state.human_inputs.append(user_answer)
                
                with st.spinner("🔄 Finalizing..."):
                    result = run_customer_support_workflow(
                        st.session_state.workflow_state["customer_name"],
                        st.session_state.workflow_state["email"],
                        st.session_state.workflow_state["query"],
                        st.session_state.human_inputs
                    )
                    st.session_state.workflow_state = result
                
                st.rerun()

# Display results
if st.session_state.workflow_state and "_human_input_needed" not in st.session_state.workflow_state:
    st.divider()
    st.subheader("📋 Support Ticket Summary")
    
    # Key information
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Ticket ID", st.session_state.workflow_state.get("ticket_id", "N/A"))
        st.metric("Priority", st.session_state.workflow_state.get("priority", "N/A").title())
    
    with col2:
        st.metric("Customer", st.session_state.workflow_state.get("customer_name", "N/A"))
        status = st.session_state.workflow_state.get("update_ticket", {}).get("status", "Processing")
        st.metric("Status", status.title() if isinstance(status, str) else "Processing")
    
    # Generated response
    response = st.session_state.workflow_state.get("response_generation", "")
    if response:
        st.subheader("💬 Our Response")
        st.info(response)
    
    # Escalation check
    escalation = st.session_state.workflow_state.get("escalation_decision", {})
    if isinstance(escalation, dict) and escalation.get("escalate"):
        st.warning("⚠️ This ticket has been escalated to a human agent for further assistance.")
    
    # Knowledge base results
    kb_result = st.session_state.workflow_state.get("knowledge_base_search", {})
    if isinstance(kb_result, dict) and kb_result.get("found"):
        st.subheader("📚 Relevant Information")
        st.success(f"**{kb_result.get('article_title', 'Solution Found')}**")
        st.write(kb_result.get("article_excerpt", ""))
    
    # Show detailed state (collapsible)
    with st.expander("🔍 View Detailed Workflow State"):
        st.json(st.session_state.workflow_state)

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About Langie")
    st.write("Langie is an AI-powered customer support agent that processes your requests through multiple stages:")
    
    stages = [
        "📥 Intake", "🧠 Understand", "🔧 Prepare", 
        "❓ Ask", "⏳ Wait", "🔍 Retrieve", 
        "🤔 Decide", "📝 Update", "✍️ Create", 
        "⚡ Execute", "✅ Complete"
    ]
    
    for stage in stages:
        st.write(f"• {stage}")
    
    st.divider()
    st.write("**Need help?** Contact our support team.")

# Reset button
if st.session_state.workflow_started:
    if st.button("🔄 Start New Request", use_container_width=True):
        st.session_state.workflow_state = None
        st.session_state.human_inputs = []
        st.session_state.workflow_started = False
        st.rerun()
