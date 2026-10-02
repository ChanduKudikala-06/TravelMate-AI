import os
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"]=certifi.where()
os.environ["REQUESTS_CA_BUNDLE"]=certifi.where()

from typing import TypedDict,Annotated
import operator
import uuid

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import(
    AnyMessage,HumanMessage,AIMessage,SystemMessage
)

from langchain_groq import ChatGroq
from tools.tavily_tool import tavily_search
from tools.flight_tool import search_flights


def get_database_url():
    
    database_url=os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("Database URL is not set in environment varaibles")
    
    if "sslmode" not in database_url:
        database_url+="?sslmode=require"
        
    return database_url


GROQ_API_KEY=os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in environment variables")


#LLM
llm=ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY
    )


#State

class TravelState(TypedDict):
    messages:Annotated[list[AnyMessage],operator.add]
    user_query:str
    flight_results:str
    hotel_results:str
    itinerary:str
    llm_calls:int

#Flight Agent
def flight_agent(state:TravelState):
    query=state["user_query"]
    flight_data=search_flights(query)
    
    return{
        "flight_results":flight_data,
        "messages":[
            AIMessage(content="Flights results fetched")
        ],
        "llm_calls":state.get("llm_calls",0)+1
        
    }
    
    
#Hotel Agent

def hotel_agent(state:TravelState):
    query=state["user_query"]
    hotel_results=tavily_search(query)
    
    return{
        "hotel_results":hotel_results,
        "messages":[
            AIMessage(content="Hotel results fetched")
        ],
        "llm_calls":state.get("llm_calls",0)+1
    }
    
    
#Itinerary Agent

def itinerary_agent(state:TravelState):
    prompt=f"""
    Create a complete travel itinerary 
    User Query:
    {state["user_query"]}
    
    Flight results:
    {state['flight_results']}
    
    Hotel results:
    {state['hotel_results']}
    
    Make the itinerary practical and budget aware, and easy to follow.
    """
    
    response=llm.invoke([
        SystemMessage(content="You are a expert travel plannner"),
        HumanMessage(content=prompt)
    ])
    
    return{
        "itinerary":response.content,
        "messages":[response],
        "llm_calls":state.get("llm_calls",0)+1
    }
    
    
#Final Agent

def final_agent(state:TravelState):
    final_prompt=f"""
    
    Generate Final travel resposne for the user
    
    User Ruquest:
    {state["user_query"]}
    
    Flights:
    {state['flight_results']}
    
    Hotels:
    {state["hotel_results"]}
    
    Itinerary:
    
    {state["itinerary"]}
    
    Format the final answer beautifully using these sections:
    1.Trip Summary
    2.Flight Details
    3.Hotel Details
    4.Day-by Day Itinerary
    5.Estimate Budget
    6.Final Recommendations
    
    Important:
    -Be clear and Practical
    -Keep the response useful for real travel planning
    """
    
    response=llm.invoke([
        SystemMessage(content="You are a professional AI travel booking assistant."),
        HumanMessage(content=final_prompt)
    ])
    
    return {
        "messages":[response],
        "llm_calls":state.get("llm_calls",0)+1
    }
    
#Build Graph

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)
    
graph.add_edge(START,"flight_agent")
graph.add_edge("flight_agent","hotel_agent")
graph.add_edge("hotel_agent","itinerary_agent")
graph.add_edge("itinerary_agent","final_agent")
graph.add_edge("final_agent",END)


#PostgresSQL Checkpointer
DATABASE_URL=get_database_url()
_conn=psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)

checkpointer=PostgresSaver(_conn)
checkpointer.setup()
travel_graph=graph.compile(checkpointer=checkpointer)


#Final Function for FastAPI

def run_travel_agent(user_input:str,thread_id:str|None=None):
    if not thread_id:
        thread_id=f"user_{uuid.uuid4().hex}"
        
    config={
        "configurable":{
            "thread_id":thread_id
        }
    }
    
    result=travel_graph.invoke(
        {
            "messages":[
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results":"",
            "hotel_results":"",
            "itinerary":"",
            "llm_calls":0
        },
        config=config
    )
    
    final_answer=result["messages"][-1].content
    
    return {
        "thread_id":thread_id,
        "answer":final_answer,
        "flight_results":result.get("flight_results",""),
        "hotel_results":result.get("hotel_results",""),
        "itinerary":result.get("itinerary",""),
        "llm_calls":result.get("llm_calls",0),
    }