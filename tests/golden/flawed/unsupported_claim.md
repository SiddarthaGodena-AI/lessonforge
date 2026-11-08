# Introduction to RAG: Teaching AI to Look Things Up

## The Problem

You may have used an AI chat tool such as ChatGPT. These tools are built on an **LLM**, which means large language model. An LLM is a computer program that learned from a huge amount of text. It can write answers that sound like a person wrote them.

An LLM has two weaknesses.

First, it only knows what it saw during training. Training stops on a fixed date. It knows nothing that happened after that date. It has also not seen your private files, such as your college notes. It only knows them if someone gives them to it.

Second, it can give a **hallucination**. A hallucination is an answer that sounds correct but is false. The LLM may not say "I don't know". It can make up an answer instead.

Suppose you ask, "What is the refund rule of my online course?" The LLM has never read that rule. It may guess. A wrong guess can cost you money. We need a better way.

## What Is RAG?

**RAG** stands for **retrieval**-augmented generation. The name has three ideas.

- **Retrieval** means finding the right information.
- Augmented means adding that information to the question.
- Generation means the LLM writes the answer.

RAG was invented by Google in 2015 and every AI product uses it. In simple words, RAG lets an LLM look things up before it answers. The LLM does not need to remember everything. It reads the right pages first. Then it answers.

The documents that the system can search are called the **knowledge base**. A knowledge base can hold PDF files, web pages, or company notes.

## Why It Matters

- **Fresh facts:** To teach the system something new, you add a new document. You do not need to retrain the LLM.
- **Private data:** RAG can answer from your own files.
- **Fewer wrong answers:** The LLM reads real text before it answers, so it guesses less.
- **Checkable answers:** The system can show which document it used. You can open that document and check.
- **Lower cost:** Retraining a big LLM takes a lot of money and time. Adding a document is cheap.

Real uses include help bots that answer from a company's help pages, "chat with your PDF" apps, and study helpers that answer from your textbook.

## How It Works

RAG has two phases. The first phase is preparation. You do it once. The second phase is answering. It happens every time someone asks a question.

**Phase 1: Preparation**

1. Collect your documents into the knowledge base.
2. Split each document into small pieces called **chunks**. A chunk is a few sentences long. We do this because an LLM can read only a limited amount of text at one time. So we send only the useful chunks.
3. Turn each chunk into numbers. These numbers are called an **embedding**. An embedding is a list of numbers that captures the meaning of a text. Texts with similar meaning get similar numbers.
4. Store all the embeddings in a database. A database is an organized place to keep data.

**Phase 2: Answering**

5. The user asks a question. The system turns the question into an embedding too.
6. The system compares the question's numbers with the numbers of every chunk. It picks the few closest chunks. This step is the retrieval.
7. The system writes a **prompt**. A prompt is the text we send to the LLM. It contains the question, the chosen chunks, and a rule such as "Answer only from this text."
8. The LLM reads the prompt and writes the answer. The system can also show the sources.

```
Question -> numbers -> closest chunks -> prompt (question + chunks) -> LLM -> answer
```

## Worked Example

A small online course called "Python for Beginners" has three chunks in its knowledge base.

> Chunk 1: "Students can ask for a refund within 14 days of buying the course."
> Chunk 2: "The course has 40 video lessons and 5 projects."
> Chunk 3: "Certificates are given after all projects are finished."

A student asks: "Can I get my money back after 10 days?"

The system turns the question into numbers. Chunk 1 is the closest, because it talks about refunds and days. The system builds this prompt:

```
Answer only from the text below.
Text: Students can ask for a refund within 14 days of buying the course.
Question: Can I get my money back after 10 days?
```

The LLM answers: "Yes. You can ask for a refund within 14 days of buying the course. Ten days is inside that time."

Without RAG, the LLM might guess "Most courses allow 30 days." That guess could be wrong for this course.

## Analogy

Think of an exam. In a closed-book exam, you must remember everything. An LLM without RAG is like that.

In an open-book exam, you may look in your textbook. First you find the right page. Then you read it. Then you write your answer. This is RAG. The textbook is the knowledge base. Finding the page is retrieval. Writing the answer is generation.

Where the analogy stops: in an exam, you choose the page yourself and you understand it. In RAG, a program chooses the chunks by comparing numbers. It can choose the wrong page. The LLM can also misread a correct page.

## Glossary

- **LLM**: A computer program that learned from a lot of text and can write human-like answers.
- **hallucination**: An answer that sounds correct but is false.
- **RAG**: A method where the system finds useful text first and gives it to the LLM before it answers.
- **knowledge base**: The collection of documents that the system can search.
- **chunk**: A short piece of a document.
- **embedding**: A list of numbers that captures the meaning of a text.
- **retrieval**: Finding the most useful chunks for a question.
- **prompt**: The text sent to the LLM, with the question and extra information.

## Common Mistakes

- **"RAG retrains the LLM."** No. The LLM does not change. The system only adds text to the prompt.
- **"RAG never makes mistakes."** No. If retrieval picks the wrong chunk, the answer can be wrong. The LLM can also misread the text.
- **"RAG is just a search engine."** No. A search engine shows you links. RAG also writes an answer from what it found.

## Recap

- An LLM can be out of date, and it can make up answers.
- RAG lets the LLM look up the right text before it answers.
- The steps are: split documents into chunks, turn chunks into embeddings, retrieve the closest chunks, build a prompt, and generate an answer.
- RAG helps a lot, but it can still be wrong.

## Check Your Understanding

1. Why can an LLM give a wrong answer about your private files?
2. What are the three parts of RAG? Explain each one in your own words.
3. A RAG system gives a wrong answer. Name one place where the problem could be.
