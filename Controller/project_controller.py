from flask import Blueprint, request, jsonify
from db import execute_query, execute_write
import logging

logger = logging.getLogger(__name__)

project_bp = Blueprint('project', __name__)

def ensure_projects_and_tracks_tables():
    try:
        # Create projects table if not exists
        execute_write("""
            CREATE TABLE IF NOT EXISTS projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                client VARCHAR(255) DEFAULT 'pwc',
                health_status ENUM('Healthy', 'At Risk', 'Critical') DEFAULT 'Healthy',
                health_score INT DEFAULT 90,
                start_date DATE,
                end_date DATE,
                status ENUM('ACTIVE', 'CLOSED') DEFAULT 'ACTIVE',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create project_tracks table if not exists
        execute_write("""
            CREATE TABLE IF NOT EXISTS project_tracks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                track_name VARCHAR(255) NOT NULL,
                description TEXT,
                status ENUM('ACTIVE', 'CLOSED') DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                INDEX (project_id)
            )
        """)
        # Clean up legacy seeded dummy projects (Agent-17 to agent25) from MySQL table
        execute_write("DELETE FROM projects WHERE LOWER(name) IN ('agent25', 'agent24', 'agent23', 'agent22', 'agent21', 'agent-20', 'agent19', 'agent-18', 'agent-17')")
    except Exception as e:
        logger.error(f"Error ensuring projects/tracks tables: {e}")

@project_bp.route('/', methods=['GET'])
def get_projects():
    ensure_projects_and_tracks_tables()
    
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    
    query = "SELECT * FROM projects WHERE 1=1"
    params = []
    
    if search:
        query += " AND (name LIKE %s OR client LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    if status and status.lower() != 'all status' and status.lower() != 'all':
        query += " AND LOWER(status) = %s"
        params.append(status.lower())
        
    query += " ORDER BY id DESC"
    
    projects = execute_query(query, tuple(params))
    
    if not projects:
        return jsonify({"success": True, "data": []})
        
    # Fetch tracks for each project dynamically from DB
    formatted_projects = []
    for p in projects:
        p_dict = dict(p)
        if p_dict.get('start_date'):
            p_dict['start_date'] = str(p_dict['start_date'])
        if p_dict.get('end_date'):
            p_dict['end_date'] = str(p_dict['end_date'])
            
        tracks = execute_query("SELECT * FROM project_tracks WHERE project_id = %s ORDER BY id ASC", (p_dict['id'],))
        p_dict['tracks'] = [dict(t) for t in tracks] if tracks else []
        formatted_projects.append(p_dict)
        
    return jsonify({"success": True, "data": formatted_projects})

@project_bp.route('/', methods=['POST'])
def create_project():
    ensure_projects_and_tracks_tables()
    data = request.json or {}
    
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "message": "Project name is required"}), 400
        
    client = data.get('client', 'pwc')
    start_date = data.get('start_date', '2026-07-01')
    end_date = data.get('end_date', '2027-02-27')
    status = data.get('status', 'ACTIVE').upper()
    description = data.get('description', '')
    tracks_input = data.get('tracks', [])
    
    new_id = execute_write(
        """INSERT INTO projects (name, client, health_status, health_score, start_date, end_date, status, description)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (name, client, 'Healthy', 90, start_date, end_date, status, description)
    )
    
    if new_id:
        created_tracks = []
        if tracks_input and len(tracks_input) > 0:
            for idx, t in enumerate(tracks_input, 1):
                t_name = t.get('track_name') or f"Track {idx}: {t.get('name', 'Main Track')}"
                t_desc = t.get('description', '')
                t_id = execute_write(
                    """INSERT INTO project_tracks (project_id, track_name, description, status)
                       VALUES (%s, %s, %s, %s)""",
                    (new_id, t_name, t_desc, 'ACTIVE')
                )
                if t_id:
                    created_tracks.append({"id": t_id, "project_id": new_id, "track_name": t_name, "description": t_desc, "status": "ACTIVE"})

        new_project = {
            "id": new_id,
            "name": name,
            "client": client,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "description": description,
            "tracks": created_tracks
        }
        return jsonify({"success": True, "data": new_project, "message": "Project created successfully with mapped tracks"})
    else:
        return jsonify({"success": False, "message": "Failed to create project"}), 500

@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    ensure_projects_and_tracks_tables()
    rows = execute_query("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not rows:
        return jsonify({"success": False, "message": "Project not found"}), 404
    
    p = dict(rows[0])
    if p.get('start_date'): p['start_date'] = str(p['start_date'])
    if p.get('end_date'): p['end_date'] = str(p['end_date'])
    
    tracks = execute_query("SELECT * FROM project_tracks WHERE project_id = %s ORDER BY id ASC", (project_id,))
    p['tracks'] = [dict(t) for t in tracks] if tracks else []
    return jsonify({"success": True, "data": p})

@project_bp.route('/<int:project_id>/tracks', methods=['POST'])
def add_track_to_project(project_id):
    ensure_projects_and_tracks_tables()
    data = request.json or {}
    track_name = data.get('track_name')
    if not track_name:
        return jsonify({"success": False, "message": "Track name is required"}), 400
        
    description = data.get('description', '')
    t_id = execute_write(
        """INSERT INTO project_tracks (project_id, track_name, description, status)
           VALUES (%s, %s, %s, %s)""",
        (project_id, track_name, description, 'ACTIVE')
    )
    if t_id:
        return jsonify({"success": True, "data": {"id": t_id, "project_id": project_id, "track_name": track_name, "description": description, "status": "ACTIVE"}})
    return jsonify({"success": False, "message": "Failed to add track"}), 500

@project_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    ensure_projects_and_tracks_tables()
    data = request.json or {}
    
    rows = execute_query("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not rows:
        return jsonify({"success": False, "message": "Project not found"}), 404
        
    p = dict(rows[0])
    name = data.get('name', p['name'])
    client = data.get('client', p.get('client', 'pwc'))
    start_date = data.get('start_date', p.get('start_date'))
    end_date = data.get('end_date', p.get('end_date'))
    status = data.get('status', p['status']).upper()
    description = data.get('description', p.get('description', ''))
    tracks_input = data.get('tracks')
    
    execute_write(
        """UPDATE projects SET name = %s, client = %s, start_date = %s, end_date = %s, status = %s, description = %s WHERE id = %s""",
        (name, client, start_date, end_date, status, description, project_id)
    )
    
    if tracks_input is not None:
        execute_write("DELETE FROM project_tracks WHERE project_id = %s", (project_id,))
        for idx, t in enumerate(tracks_input, 1):
            t_name = t.get('track_name') or f"Track {idx}: {t.get('name', 'Main Track')}"
            t_desc = t.get('description', '')
            t_status = t.get('status', 'ACTIVE')
            execute_write(
                """INSERT INTO project_tracks (project_id, track_name, description, status)
                   VALUES (%s, %s, %s, %s)""",
                (project_id, t_name, t_desc, t_status)
            )
            
    updated_rows = execute_query("SELECT * FROM projects WHERE id = %s", (project_id,))
    res_p = dict(updated_rows[0])
    if res_p.get('start_date'): res_p['start_date'] = str(res_p['start_date'])
    if res_p.get('end_date'): res_p['end_date'] = str(res_p['end_date'])
    
    tracks = execute_query("SELECT * FROM project_tracks WHERE project_id = %s ORDER BY id ASC", (project_id,))
    res_p['tracks'] = [dict(t) for t in tracks] if tracks else []
    return jsonify({"success": True, "data": res_p, "message": "Project updated successfully"})

@project_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    ensure_projects_and_tracks_tables()
    rows = execute_query("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not rows:
        return jsonify({"success": False, "message": "Project not found"}), 404
        
    execute_write("DELETE FROM projects WHERE id = %s", (project_id,))
    return jsonify({"success": True, "message": f"Project {project_id} deleted successfully"})

@project_bp.route('/tracks/<int:track_id>', methods=['PUT'])
def update_track(track_id):
    ensure_projects_and_tracks_tables()
    data = request.json or {}
    track_name = data.get('track_name')
    description = data.get('description', '')
    status = data.get('status', 'ACTIVE')
    
    execute_write(
        """UPDATE project_tracks SET track_name = %s, description = %s, status = %s WHERE id = %s""",
        (track_name, description, status, track_id)
    )
    return jsonify({"success": True, "message": f"Track {track_id} updated successfully"})

@project_bp.route('/tracks/<int:track_id>', methods=['DELETE'])
def delete_track(track_id):
    ensure_projects_and_tracks_tables()
    execute_write("DELETE FROM project_tracks WHERE id = %s", (track_id,))
    return jsonify({"success": True, "message": f"Track {track_id} deleted successfully"})
