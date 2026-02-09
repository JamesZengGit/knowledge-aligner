# Knowledge Aligner

An AI-powered decision tracking system for hardware engineering teams that automatically captures, organizes, and surfaces critical engineering decisions from team communications.

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- (Optional) OpenAI API key for AI features

### Setup
```bash
# Clone repository
git clone https://github.com/JamesZengGit/knowledge-aligner.git
cd knowledge-aligner

# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install fastapi uvicorn openai

# Copy environment file
cp .env.example .env
# Add your OpenAI API key to .env if desired
```

### Run Application
```bash
# Start backend (terminal 1)
cd backend
python simple_server.py

# Start frontend (terminal 2)
cd frontend
npm run dev
```

### Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Features

### Decision Tracking
- Indexed decisions with before/after comparisons
- Complete impact analysis showing affected components and stakeholders
- Full traceability with citations back to original discussions

### Gap Detection
- Missing stakeholder alerts when key people aren't included in decisions
- Role-based personalized notifications with meeting host contact info
- Entity relationship tracking for proper accountability

### Role-Based Personalization
- Account switching between different engineering roles
- Component-specific gaps and priorities for each team member
- Personalized chat interface with AI-powered insights

### Smart Prioritization
- Drag-and-drop gap priority management
- Dynamic priority calculation based on component overlap
- Chat integration that recognizes reordered priorities

## Technology Stack

### Frontend
- Next.js 14 with TypeScript
- Tailwind CSS for styling
- React components for UI

### Backend
- FastAPI with Python
- OpenAI GPT-4o-mini for chat responses
- In-memory data for demo purposes

### Key Capabilities
- Real-time account switching
- Dynamic gap priority management
- Entity-linked notifications
- Chat persistence across tab navigation

## Demo Accounts

The application includes three demo accounts showing different engineering perspectives:

### Alice Chen (Mechanical Lead)
- **Components**: Motor-XYZ, Bracket-Assembly
- **Gaps**: Missing from motor torque requirement decisions
- **Priorities**: Hardware design and mechanical integration focus

### Bob Wilson (Firmware Engineer)
- **Components**: ESP32-Firmware, Bootloader
- **Gaps**: Missing from security and motor control meetings
- **Priorities**: Firmware updates and embedded system coordination

### Dave Johnson (Hardware Lead)
- **Components**: PCB-Rev3, Power-Supply-v2
- **Gaps**: Missing from power requirement discussions
- **Priorities**: Power systems and PCB design decisions

### Role Switching
Click the user avatar in the header to switch between accounts and see how the system adapts to different engineering roles with personalized gaps, priorities, and notifications.

## Demo Scenarios

### Motor Torque Requirement Change
- Requirement change from 15nm to 22nm affects multiple components
- Gap detection identifies missing firmware engineer in decision
- Cross-team coordination needed for Motor-XYZ, ESP32-Firmware, and power systems

### Security Update Implementation
- Bootloader security requirements affect firmware components
- Missing stakeholder alerts notify affected team members
- Meeting host contact information provided for proper inclusion

### Power System Design Review
- PCB and power supply changes require hardware lead input
- Entity linking tracks relationships between components and owners
- Personalized notifications ensure proper engineering review