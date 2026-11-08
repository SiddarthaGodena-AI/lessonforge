# Introduction to RAG

## The Problem
Imagine you study for a big board exam. You read many books for months. Then, your exams end. 

After that day, you do not read new books. You do not know new events. 

A computer program called a **large language model (LLM)** has the same problem. An LLM is a computer program trained on huge amounts of text to generate words. It only knows facts up to its **training cutoff date**, which is the date after which a model was not trained on any new data. It does not know private files, such as your school fees receipt or college forms.

When an LLM does not know an answer, it still tries to guess. It produces a **hallucination**. A hallucination is a fluent answer from an AI that is false or unsupported. It sounds very confident, but it is incorrect.

## What Is RAG?
We can fix this issue using **retrieval-augmented generation (RAG)**. This is a method where an AI searches external documents to find facts before it answers a question. 

First, the system looks for the right information in a storage area called a **knowledge base**. A knowledge base is an organized collection of documents used to look up facts. 

Then, it gives those facts to the model. The model writes the final answer using those facts.

RAG does not retrain the LLM's weights when a new document is added to the knowledge base.

## Why It Matters
With this new method, you do not retrain the model. Its internal weights do not change. 

You only update the files in your document store. You can add new notes today, and the system uses them immediately.

This method also lets you see the source. You can check which page or note the answer came from. It helps students and offices read their own private notes safely.

## How It Works
Here is the step-by-step process:

1. **Break the text into pieces**: A model cannot read an entire library at once. It can only process a limited amount of text at one time. So, we cut long documents into smaller parts. Each small part of a document is called a **chunk**.
2. **Convert text to numbers**: A computer cannot understand words directly. It uses an **embedding**, which is a list of numbers that represents the meaning of a text. Texts with similar meanings get similar lists of numbers.
3. **Save the numbers**: We save these number lists into a searchable database.
4. **Search for answers**: You ask a question. The system turns your question into numbers too. Then comes **retrieval**, which is the process of searching and finding the most relevant pieces of text for a question. It finds the pieces with the closest numbers to your question.
5. **Build the instruction**: The system takes your question and the found pieces. It puts them together into a **prompt**. A prompt is the input text or instruction sent to an LLM.
6. **Generate the answer**: The model reads this instruction and writes an answer using only those facts.

## Worked Example
Let us look at a simple college example.

**The Question:**
"What is the last date to submit the physics practical file?"

**The Retrieved Chunk:**
The system searches the college notice board files. It finds one small chunk:
"Notice: All Class 12 students must submit their physics practical files to Room 10 by March 15."

**The Prompt:**
The system builds this prompt for the model:
"Use the following text to answer the question.
Text: Notice: All Class 12 students must submit their physics practical files to Room 10 by March 15.
Question: What is the last date to submit the physics practical file?"

**The Final Answer:**
The model generates:
"The last date to submit your physics practical file is March 15."

## Analogy
Think of an open-book exam. 

Without this method, an exam is closed-book. You must write everything from memory. If you forget, you might guess and make a mistake.

With this method, the exam becomes an open-book exam. You have your textbook on your desk. When a question appears, you turn to the correct page. You read the exact line, and then you write your answer.

Where the analogy stops: A human student understands the whole book over time. A computer only matches numbers to pull small text pieces without real human understanding.

## Glossary
- **LLM**: A computer program trained on huge text to understand and generate human language.
- **training cutoff date**: The date after which an AI model was not trained on any new data.
- **hallucination**: A fluent answer from an AI model that is false or unsupported by facts.
- **RAG**: A method that finds relevant documents first to help an AI model write accurate answers.
- **knowledge base**: An organized collection of documents and data used to find information.
- **chunk**: A small piece of text cut from a larger document for processing.
- **embedding**: A list of numbers that represents the meaning of a text piece.
- **retrieval**: The process of finding the most relevant text pieces for a user question.
- **prompt**: The complete text and instructions sent to an AI model to get an answer.

## Common Mistakes
- **Thinking RAG retrains the model**: It does not retrain the model. The model stays the same, but it reads new text provided inside the prompt.
- **Believing errors are completely gone**: This method reduces false guesses, but it does not remove all errors. If the model misreads the text, it can still make a mistake.
- **Assuming search is always correct**: If the system finds wrong or useless text chunks, the final answer will also be wrong.

## Recap
- Models only know their old training data and lack your private notes.
- Models can make confident, false guesses called hallucinations.
- This technique cuts documents into small chunks and turns their meaning into numbers.
- The system finds the closest text chunks to your question and adds them to the input.
- You can update knowledge anytime just by changing your files, without retraining.

## Check Your Understanding
1. Why do we cut long documents into small chunks before saving them?
2. What happens to the internal weights of an AI model when you add new documents to a knowledge base?
3. If the search step picks the wrong text chunk, what will happen to the final answer?
