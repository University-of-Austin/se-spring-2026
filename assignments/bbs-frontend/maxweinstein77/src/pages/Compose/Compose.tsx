// Standalone /compose route. Renders the shared ComposeForm in its
// full-card layout. (Feed also uses ComposeForm inline at the top.)

import { useNavigate } from "react-router-dom";
import { ComposeForm } from "../../components/ComposeForm";
import styles from "./Compose.module.css";

export function Compose() {
  const navigate = useNavigate();
  return (
    <section className={styles.wrap}>
      <h1 className={styles.heading}>Compose</h1>
      <ComposeForm onPosted={() => navigate("/")} />
    </section>
  );
}
