# Introduction to RAG

## The Problem
Imagine you study for a big board exam. You read many books until March. After March, you close all books. You cannot read anything new.

Now someone asks you about news from April. You did not read it. What happens? You might guess. You might sound very confident, but your answer is completely wrong.

A computer program called a **large language model (LLM)** has the same problem. An LLM is an AI program trained on huge amounts of text to understand and generate human language. It only knows facts up to its training cutoff date. It does not know newer events. It also does not know your school's private notices or personal notes. 

When it does not know an answer, it can create a **hallucination**. A hallucination is a fluent answer from an AI that sounds convincing but is false.

## What Is RAG?
To fix this problem, researchers created **retrieval-augmented generation (RAG)**. This is a method where an AI searches external documents to find facts before generating an answer. 

Instead of guessing, the AI first finds the right pages. Then it reads those pages to write the final answer.

## Why It Matters
First, your college or office has private files. An LLM has not seen your private documents. With RAG, the model can answer questions using those files.

Second, facts change often. In simple AI systems, updating knowledge requires retraining the model. Retraining is slow and difficult. With RAG, you simply add or change the saved documents. The model does not need retraining.

Third, RAG helps you trust the system. It can show which exact lines or notes it used. You can check the source yourself.

## How It Works
A RAG system follows these clear steps:

1. Collect files: You collect your notes or textbooks into a **knowledge base**. A knowledge base is a central collection of stored documents used to find information.
2. Cut into pieces: An LLM can only read a limited amount of text at one time. Because of this limit, the system cuts long files into small parts. A **chunk** is a short piece of text cut from a larger document.
3. Turn text into numbers: The system converts each piece into an **embedding**. An embedding is a list of numbers that represents the meaning of a piece of text. Texts with similar meanings get similar lists of numbers.
4. Store numbers: These numbers are saved in a special list.
5. Search for facts: You type a question. The system turns your question into numbers too. Then it performs **retrieval**. Retrieval is the process of searching and fetching the most relevant text pieces for a question.
6. Build the message: The system takes the best pieces and pastes them next to your question. This combined text forms a **prompt**. A prompt is the input text or instruction given to an AI model.
7. Generate the answer: The LLM reads the full message. It uses the retrieved facts to write the correct response.

## Worked Example
Let us look at a simple college example.

A student asks this question:
"What is the last date to submit the physics project?"

The college office uses a RAG system. The system searches the college notice files.

The system finds this exact retrieved text:
"Notice 42: All Class 12 students must submit their physics project by 15 November to Room 10."

Next, the system creates the full message for the LLM:
"Read this text: Notice 42: All Class 12 students must submit their physics project by 15 November to Room 10.
Question: What is the last date to submit the physics project?
Answer the question using only the text above."

The LLM reads this message and generates the final output:
"The last date to submit the physics project is 15 November."

## Analogy
Think of two different exams in school.

The first exam is a closed-book exam. You must write answers only from your memory. If you forgot a formula, you might guess. Your guess might be wrong. This is how an AI acts without extra tools.

The second exam is an open-book exam. The teacher allows you to keep your notebook on the desk. When a question appears, you open the correct page. You read the formula from the page. Then you write your answer. This open-book method is like RAG.

Where the analogy stops: A human student understands the whole book naturally. A RAG system must first cut the book into tiny pieces and turn words into numbers before it can search.

## Glossary
- **LLM**: An AI program trained on large amounts of text to understand and generate human language.
- **hallucination**: A fluent answer from an AI model that sounds confident but is false or unsupported.
- **RAG**: A method where an AI searches external documents to find facts before generating an answer.
- **knowledge base**: A central collection of stored documents and data used to find information.
- **chunk**: A short piece of text cut from a larger document for easier reading by an AI.
- **embedding**: A list of numbers that represents the meaning of a piece of text.
- **retrieval**: The process of searching and fetching the most relevant text pieces for a question.
- **prompt**: The input text, question, or instruction given to an AI model to produce an answer.

## Common Mistakes
- **Mistake 1**: Thinking RAG retrains the model.  
  *Correction*: RAG does not change the model's weights. It only passes helpful text along with your question.

- **Mistake 2**: Thinking RAG stops all mistakes completely.  
  *Correction*: RAG reduces errors, but hallucinations can still happen. If the system fetches the wrong text, the answer can be wrong.

- **Mistake 3**: Thinking RAG connects the AI to the live internet automatically.  
  *Correction*: A basic RAG system only searches the specific documents you place in its private store.

## Recap
- AI models do not know events after their training cutoff and cannot see private files.
- RAG lets an AI search a document store to find useful facts before writing an answer.
- Long documents are split into small parts because an AI model can only read limited text at once.
- Meanings are stored as numbers so the system can find pieces with similar meanings.
- You can update the facts anytime by adding new documents without retraining the AI.

## Check Your Understanding
1. Why must long documents be split into smaller pieces before an AI model reads them?
2. How does the system update its knowledge when college rules change?
3. What can happen to the final answer if the system fetches irrelevant text pieces?
