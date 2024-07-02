from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_community.utilities import SQLDatabase
from langchain.tools import BaseTool
from sqlalchemy.orm import Session
from langchain.agents import AgentExecutor, Tool
from langchain.prompts import PromptTemplate
from model1 import llm
#I am using a local llm model, replace this import with your OpenAI api keys

DATABASE_URL = "mysql+mysqlconnector://username:pw@localhost/databasename"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    with engine.connect() as conn:
        print("Connected successfully!")
except Exception as e:
    print("Connection failed:", e)


class MySQLQueryTool(BaseTool):
    name = "mysql_query_tool"
    description = "Tool to run SQL queries on a MySQL database"
    def __init__(self, session):
        super().__init__()

    def _run(self, query: str) -> str:
        try:
            result = self.session.execute(query)
            rows = result.fetchall()
            return str(rows)
        except Exception as e:
            return str(e)


db = SQLDatabase.from_uri(DATABASE_URL)
print(db.dialect)
print(db.get_usable_table_names())

context = db.get_context()
print(list(context))
mydbcontext=context["table_info"]
print(mydbcontext)

session = SessionLocal()

llm=llm #define your llm here
mysql_query_tool = MySQLQueryTool(session=session)

ptemplate = """
You are an agent designed to interact with a MySQL database. You can use the following tool to help you:

- mysql_query_tool: Run SQL queries on a MySQL database.

You are a MySQL expert. Given an input question, first create a syntactically correct SQLite query to run, then look at the results of the query and return the answer to the input question.Use the tool for this task.
Unless the user specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT clause as per MySQL. You can order the results to return the most informative data in the database.
Never query for all columns from a table. You must query only the columns that are needed to answer the question.Pay attention to the tables present in the database. Wrap each column name in double quotes (") to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use date('now') function to get the current date, if the question involves "today".

Use the following format:

Question: Question here
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer here

Here is the user question: {input}

use the following tables:
{context}

"""
prompt = PromptTemplate(input_variables=["input","context"],template=ptemplate)

tools=[Tool(name='mysql_query_tool',func=mysql_query_tool.run,description=mysql_query_tool.description)]

from langchain.agents import AgentExecutor, Tool
from langchain.prompts import PromptTemplate
from langchain.agents.format_scratchpad.openai_tools import (format_to_openai_tool_messages,)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
agent = (
    {
        "input": lambda x: x["input"],
        "context": lambda x: x["context"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(x["intermediate_steps"]),
    }
    | prompt
    | llm
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def run_agent(input_text: str):
    return agent_executor({"input": input_text,"context":mydbcontext})

response = run_agent("How many employees are there in the database?")
print(response["output"])


