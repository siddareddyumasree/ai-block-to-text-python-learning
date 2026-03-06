# AI-Powered Block-to-Text Python Learning Platform

An AI-driven educational platform designed to help beginners transition from **block-based programming to text-based Python coding**.

The system combines **Blockly visual programming, real-time Python execution, and a fine-tuned Large Language Model (Phi-2)** to provide coding practice, debugging assistance, and concept explanations for beginner programmers.

This project was developed as a **Master’s Dissertation Project in Computer Science**.

---

# Overview

Many beginners struggle when transitioning from visual programming environments such as **Scratch or Blockly** to **text-based programming languages like Python**.

Block environments hide syntax complexity, while text programming requires understanding of indentation, punctuation, and error messages.

This project introduces an **AI-powered learning platform** that supports this transition by combining:

- visual block programming
- automatic Python code generation
- real-time code execution
- AI debugging assistance
- topic-based Python question generation

The goal is to provide a **guided pathway from visual logic building to real programming**.

---

# Key Features

## Block-Based Programming
Users can construct programs visually using **Blockly blocks** that represent Python logic structures.

## Automatic Code Generation
The system converts block-based programs into **Python code automatically**, allowing learners to see how visual logic translates into text-based syntax.

## Python Code Editor
A built-in editor allows students to write and run Python programs directly.

## Real-Time Python Execution
Python code runs safely in the browser using **Pyodide**, enabling instant feedback without server-side execution.

## AI Debugging Assistant
A chatbot powered by a **fine-tuned Phi-2 language model** provides debugging help and explanations.

## AI Question Generator
Students can generate Python practice questions based on selected topics.

## Progress Tracking
Student activity and solutions are stored in a **MySQL database** to track learning progress.

---

# System Architecture

The system follows a modular architecture consisting of five main layers.

Frontend  
HTML, CSS, Bootstrap, JavaScript, Blockly

Backend  
Flask web server handling authentication, APIs, and AI communication

Database  
MySQL database storing user information and learning history

AI Layer  
Fine-tuned Phi-2 Large Language Model running via llama.cpp

Execution Environment  
Pyodide browser-based Python runtime

---

# Technology Stack

Frontend
- HTML
- CSS
- Bootstrap
- JavaScript
- Blockly
- PrismJS

Backend
- Python
- Flask
- Flask-Login
- bcrypt

Database
- MySQL
- SQLAlchemy ORM

AI / Machine Learning
- Phi-2 Large Language Model
- LoRA fine-tuning
- HuggingFace Transformers
- PEFT

Python Execution
- Pyodide

Model Inference
- llama.cpp

---




# AI Model

The AI assistant is based on **Microsoft Phi-2**, a lightweight transformer model designed for reasoning and coding tasks.

The model was fine-tuned using **LoRA (Low-Rank Adaptation)** to specialize it for:

- beginner Python question generation
- debugging explanations
- conceptual tutoring

### Why Phi-2

- lightweight architecture
- efficient inference
- strong reasoning performance
- suitable for deployment on limited hardware

---

# Dataset

The training dataset was built by combining multiple sources.

Sources used

CodeAlpaca dataset  
StackOverflow Python question-answer dataset  
Kaggle beginner Python problems dataset  
Custom dataset of beginner programming mistakes

You can access the dataset from here: https://huggingface.co/datasets/uma-siddareddy/phi2-block-to-text-python-education-dataset 

The custom dataset focused on common beginner errors such as:

- missing colons
- indentation errors
- incorrect loop ranges
- type mismatches

This allowed the model to produce **short and beginner-friendly explanations**.

---

# Model Training

The model was fine-tuned using **LoRA parameter-efficient fine-tuning**.

Training configuration:
Batch size: 4
Gradient accumulation steps: 2
Learning rate: 2e-4
Epochs: 3
Sequence length: 512
LoRA rank: 8
LoRA alpha: 16
LoRA dropout: 0.05
Optimizer: AdamW


Training was executed on **RunPod cloud GPUs**.

Training duration:

- Question generation model: ~5 hours
- Chatbot fine-tuning: ~20 hours

The final merged model size is approximately **11–12 GB**.

Model is availabe at: https://huggingface.co/uma-siddareddy/phi-2-block-t0-text-python-learning 

---

# System Fine-tuning workflow

<img width="470" height="856" alt="image" src="https://github.com/user-attachments/assets/617eb406-5b62-40d1-8f74-b83e7e3690aa" />

# Evaluation

The system was evaluated using both automated metrics and manual analysis.

Evaluation methods:

Manual rubric evaluation  
BLEU score  
METEOR score  
Saved interaction analytics

Manual evaluation assessed:

- clarity of explanations
- correctness of debugging
- age-appropriate language
- minimal response verbosity


---

# Example Workflow

1. User logs into the system  
2. User generates a Python programming question  
3. User solves the problem using Blockly blocks  
4. Blocks are converted into Python code  
5. Code runs in the browser using Pyodide  
6. AI chatbot provides debugging help if needed  
7. Solutions are saved to the database



---

# Security and Privacy

User passwords are stored using **bcrypt hashing**.

Code execution occurs in the browser via **Pyodide**, reducing security risks associated with server-side code execution.

Only minimal user information is stored.

---

# Future Work

Several improvements can extend this system.

- usability testing using SUS surveys
- acceptance evaluation using TAM frameworks
- expansion of training datasets
- support for advanced Python concepts
- deployment using cloud infrastructure
- integration with school learning platforms

---

# Demo

A demonstration video of the system is available in the `demo` directory.

The demo shows:

- question generation
- block-based problem solving
- Python code execution
- AI debugging assistance

---

# Author

Master’s Dissertation Project  
Department of Computer Science  
University of Warwick

---

# License

This project is licensed under the MIT License.

