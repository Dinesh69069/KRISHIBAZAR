import type { Metadata } from 'next';
import Footer from '../components/Footer';

export const metadata: Metadata = {
  title: 'Team | KrishiBazar AI',
  description: 'The student team building price forecasts and mandi rankings for Odisha farmers.',
};

type Member = {
  name: string;
  role: string;
  lead?: boolean;
  photo?: string;
};

const TEAM: Member[] = [
  {
    name: 'Dinesh Kumar Sahoo',
    role: 'Project Lead',
    lead: true,
    photo: '/team/Dinesh.jpg',
  },
  {
    name: 'Satyajit Behera',
    role: 'Frontend',
    photo: '/team/Satyajit.png',
  },
  {
    name: 'Digal Dibyajyoti',
    role: 'ML and Data',
    photo: '/team/Digal.jpeg',
  },
  {
    name: 'Harddik Srichandanray',
    role: 'Backend',
    photo: '/team/Harddik.jpeg',
  },
  {
    name: 'Subham Kumar Sahoo',
    role: 'System Architect',
    photo: '/team/Subham.jpeg',
  },
  {
    name: 'Nikhilesh Behera',
    role: 'Deployment',
    photo: '/team/Nikhilesh.jpeg',
  },
];

const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

export default function TeamPage() {
  return (
    <div className="kb kb-page">
      <div className="wrap">
        <div className="t-head">
          <h1>The people behind KrishiBazar AI</h1>
          <p>A small student team building price forecasts and mandi rankings for Odisha&apos;s farmers.</p>
        </div>

        <div className="roster">
          {TEAM.map((m, i) => (
            <div key={i} className={`member${m.lead ? ' lead' : ''}`}>
              <div className={`avatar${m.photo ? ' has-photo' : ''}`} aria-hidden={!m.photo}>
                {m.photo ? <img src={m.photo} alt={m.name} /> : initials(m.name)}
              </div>
              <div>
                <h3>{m.name}</h3>
                <span className={`tag${m.lead ? ' a' : ''}`}>{m.role}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="affil">
          <div>
            <p className="sub">Institution</p>
            <h3>N.I.E.L.I.T.</h3>
            <p>Department of AI</p>
          </div>
          <div>
            <p className="sub">Mentor</p>
            <h3>Bijayalaxmi Behera</h3>
            <p>Academic Mentor</p>
          </div>
          <div>
            <p className="sub">Data</p>
            <h3>Open Government Data</h3>
            <p>Data.gov.in, Ministry of Agriculture</p>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
