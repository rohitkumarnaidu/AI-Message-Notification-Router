# Contributing to Message Notification Router

First off, thank you for considering contributing to the Message Notification Router! It's people like you that make open source such a great community.

## Setting up the Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/hackerrank-orchestrate-august26.git
   cd hackerrank-orchestrate-august26
   ```

2. **Install dependencies:**
   For the backend (Python):
   ```bash
   pip install -r requirements.txt
   ```
   For the frontend (Next.js):
   ```bash
   cd frontend
   npm install
   ```

3. **Run the services:**
   You can run everything via Docker Compose:
   ```bash
   docker-compose up --build
   ```

4. **Run Tests:**
   Ensure all tests pass before submitting a pull request.
   ```bash
   pytest
   ```
   *(Note: No network calls are allowed in tests. Please mock API interactions.)*

## Code Style Guidelines

- **Python:** Follow PEP 8 guidelines. We recommend using `black` for formatting and `flake8` for linting.
- **Frontend (TypeScript):** Follow standard TypeScript practices and the established TailwindCSS structure.

## Submitting a Pull Request

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally.
3. **Branch:** Create a new branch for your feature or bugfix (`git checkout -b feature/your-feature-name`).
4. **Commit:** Make your changes and commit them with descriptive messages.
5. **Push** to your fork (`git push origin feature/your-feature-name`).
6. **Create a Pull Request:** Open a PR against the `main` branch of the original repository.

## Reporting Bugs

We use GitHub Issues to track bugs. When reporting a bug, please include:
- A clear and descriptive title.
- Steps to reproduce the bug.
- Expected behavior vs actual behavior.
- Relevant logs or screenshots.
- Your environment details (OS, Python version, Node.js version, etc.).

## Testing Requirements
- All tests must pass in the CI pipeline.
- Do not make external network calls in tests; mock all external dependencies.
- Add tests for new features or bug fixes.

## Code Review Process
All submissions require review. We may ask for changes before a PR is merged to ensure code quality and consistency.

## License
By contributing, you agree that your contributions will be licensed under its MIT License.
