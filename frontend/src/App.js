import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { Navbar, Nav, Container } from 'react-bootstrap';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import Insights from './pages/Insights';
import StudentProfile from './pages/StudentProfile';
import './App.css';

function App() {
  return (
    
      <div className="App">
        <Navbar bg="dark" variant="dark" expand="lg">
          <Container>
            <Navbar.Brand href="/">EWS Dashboard</Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
              <Nav className="me-auto">
                <Nav.Link href="/">Dashboard</Nav.Link>
                <Nav.Link href="/students">Students</Nav.Link>
                <Nav.Link href="/insights">Insights</Nav.Link>
              </Nav>
            </Navbar.Collapse>
          </Container>
        </Navbar>

        <Container className="mt-4">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/students" element={<Students />} />
            <Route path="/students/:id" element={<StudentProfile />} />
            <Route path="/insights" element={<Insights />} />
          </Routes>
        </Container>
      </div>
    
  );
}

export default App;
