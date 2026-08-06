CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generation_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_name VARCHAR(255) NOT NULL,
    application_id VARCHAR(255) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    requested_by VARCHAR(255),
    status ENUM('draft','in_progress','validated','packaged','approved','rejected','rework') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (status),
    INDEX (created_at)
);

CREATE TABLE IF NOT EXISTS generation_specs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    source_topics TEXT,
    target_topics TEXT,
    consumer_group VARCHAR(255),
    state_store_needed BOOLEAN DEFAULT FALSE,
    error_topic_policy VARCHAR(255),
    schema_hints TEXT,
    normalized_by ENUM('ai','manual'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id)
);

CREATE TABLE IF NOT EXISTS pattern_matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    pattern_type ENUM('single_topic','multi_topic_stateful','error_topic','correlation', 'standards'),
    source_reference VARCHAR(255),
    similarity_score FLOAT,
    cited_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id)
);

CREATE TABLE IF NOT EXISTS blueprints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    file_manifest TEXT,
    class_design TEXT,
    generated_rationale TEXT,
    status ENUM('draft','approved') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id),
    INDEX (status)
);

CREATE TABLE IF NOT EXISTS generated_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    file_name VARCHAR(255),
    file_path VARCHAR(512),
    file_type ENUM('java','yaml','xml','md','test'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id)
);

CREATE TABLE IF NOT EXISTS validation_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    rule_name VARCHAR(255),
    passed BOOLEAN,
    severity ENUM('info','warning','error'),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id),
    INDEX (severity)
);

CREATE TABLE IF NOT EXISTS packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    zip_path VARCHAR(512),
    validation_summary TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    reviewer_name VARCHAR(255),
    decision ENUM('approved','rework','rejected'),
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT,
    agent_name VARCHAR(255),
    action VARCHAR(255),
    input_summary TEXT,
    output_summary TEXT,
    model_used VARCHAR(255),
    prompt_version VARCHAR(255),
    tokens_used INT,
    error_message TEXT,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id),
    INDEX (created_at)
);

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    job_status ENUM('queued','running','completed','failed') DEFAULT 'queued',
    current_step VARCHAR(255),
    step_log TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP NULL,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (request_id),
    INDEX (job_status)
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    question TEXT,
    answer TEXT,
    request_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES generation_requests(id) ON DELETE CASCADE,
    INDEX (session_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    action VARCHAR(255) NOT NULL,
    prompt_text TEXT,
    entity_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
