# PerForge

Welcome to PerForge, the ultimate tool for automating performance testing and report generation. PerForge makes your life easier by seamlessly integrating data collection, analysis, and reporting in one place.

## What is PerForge?

PerForge is a tool designed to automate performance testing reporting tasks. It works effortlessly with InfluxDB and Grafana to gather metrics, generate graphs, and compile insightful reports. Additionally, it leverages AI for deeper performance analysis.

## Why use PerForge?

Manual performance test reporting is time-consuming. PerForge automates these processes, allowing you to:

- ⏱ **Save time:** Reduce manual tasks and speed up your workflow.
- 🤖 **Gain insights:** Utilize AI for comprehensive performance analysis.
- 📋 **Generate detailed reports:** Produce reports in multiple formats like Mail, PDF, Atlassian Confluence, Jira, and Azure Wiki.

## Key Features

- **Automated data collection & integration:** Connects with InfluxDB and Grafana, and supports JMeter data.
- **Project & secret management:** Manage multiple projects and centralized secrets with controlled access.
- **Seamless integration setup:** Easy configuration for InfluxDB, Grafana, and AI services (Gemini, OpenAI, Azure OpenAI).
- **Flexible report generation:** Generate reports in various formats with AI-driven insights and customizable prompts.
- **Automated NFR comparison:** Compare test results against predefined Non-Functional Requirements (NFRs) and calculate APDEX values.
- **UI interface & API:** Intuitive interface for easy report generation and API support for CI integration.

## Tech Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Database:** InfluxDB, PostgreSQL (via psycopg2)
- **Frontend:** Jinja2
- **AI:** LangChain, Google Gemini, OpenAI
- **Containerization:** Docker
- **Monitoring:** Grafana

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your machine.

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/PerForge.git
    cd PerForge
    ```

2.  **Run the application:**

    You can run the entire stack (PerForge, Grafana, InfluxDB) or just the services you need.

    - To run the complete stack:
      ```sh
      docker-compose up -d
      ```
    - To run only PerForge:
      ```sh
      docker-compose up -d perforge
      ```

3.  **Access the application:**

    The services will be available on the following ports:
    - **PerForge UI:** 7878
    - **Grafana:** 3000
    - **InfluxDB:** 8086

## Usage

Once the application is running, you can start by:

1.  Creating a new project.
2.  Configuring your InfluxDB and Grafana connections.
3.  Setting up your AI service provider.
4.  Generating your first performance report.

For more detailed instructions, check out our official documentation: [Perforge docs](https://perforge.app/docs/installation/docker).

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
