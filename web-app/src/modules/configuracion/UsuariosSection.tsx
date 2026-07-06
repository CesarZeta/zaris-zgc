// Configuración → Usuarios y permisos (Fase 6.5 RBAC).
// Tres bloques (diseño en docs/DISENO-USUARIOS-Y-PERMISOS.md §6):
//   1. Usuarios: alta/edición, rol, nivel POS, activar/desactivar, reset de clave.
//   2. Roles: los 5 de sistema (read-only, clonables) + roles propios del tenant.
//   3. Matriz: módulos × (— / Ver / Editar / Anular) del rol seleccionado.
// El backend re-valida todo (403 sin permiso; anti-lockout en 422).

import { useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost, apiPut } from "../../lib/api";
import { tienePermiso } from "../../lib/auth";
import type { CatalogoPermisos, Rol, UsuarioAdmin } from "../../lib/types";

interface FormUsuario {
  id: string | null;
  email: string;
  nombre: string;
  password: string;
  rol_id: string;
  nivel_acceso: number;
  activo: boolean;
}

const USUARIO_VACIO: FormUsuario = {
  id: null,
  email: "",
  nombre: "",
  password: "",
  rol_id: "",
  nivel_acceso: 3,
  activo: true,
};

const NIVELES_POS = [
  { valor: 1, texto: "1 — Administrador" },
  { valor: 2, texto: "2 — Supervisor (autoriza anulaciones POS)" },
  { valor: 3, texto: "3 — Operador" },
];

const ACCION_TEXTO: Record<string, string> = { ver: "Ver", editar: "Editar", anular: "Anular" };

export default function UsuariosSection() {
  const puedeEditar = tienePermiso("configuracion", "editar");

  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [roles, setRoles] = useState<Rol[]>([]);
  const [catalogo, setCatalogo] = useState<CatalogoPermisos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const [formUsuario, setFormUsuario] = useState<FormUsuario | null>(null);
  const [rolSel, setRolSel] = useState<Rol | null>(null);
  const [matriz, setMatriz] = useState<Record<string, string>>({});
  const [nombreNuevoRol, setNombreNuevoRol] = useState<string | null>(null);

  async function cargar() {
    const [u, r, c] = await Promise.all([
      apiGet<UsuarioAdmin[]>("/usuarios"),
      apiGet<Rol[]>("/roles"),
      apiGet<CatalogoPermisos>("/permisos/catalogo"),
    ]);
    setUsuarios(u.data);
    setRoles(r.data);
    setCatalogo(c.data);
    return r.data;
  }

  useEffect(() => {
    cargar().catch((e) =>
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar usuarios y roles"),
    );
  }, []);

  function rolNombre(rol_id: string | null): string {
    if (!rol_id) return "— (acceso total)";
    return roles.find((r) => r.id === rol_id)?.nombre ?? "?";
  }

  function avisar(txt: string) {
    setMensaje(txt);
    setError(null);
  }

  function fallo(e: unknown, generico: string) {
    setError(e instanceof ApiError ? e.message : generico);
    setMensaje(null);
  }

  // ===== Usuarios =====

  async function guardarUsuario() {
    if (!formUsuario || ocupado) return;
    setOcupado(true);
    try {
      if (formUsuario.id) {
        await apiPut(`/usuarios/${formUsuario.id}`, {
          nombre: formUsuario.nombre.trim(),
          rol_id: formUsuario.rol_id || null,
          nivel_acceso: formUsuario.nivel_acceso,
          activo: formUsuario.activo,
        });
        avisar("Usuario actualizado.");
      } else {
        await apiPost("/usuarios", {
          email: formUsuario.email.trim().toLowerCase(),
          nombre: formUsuario.nombre.trim(),
          password: formUsuario.password,
          rol_id: formUsuario.rol_id,
          nivel_acceso: formUsuario.nivel_acceso,
        });
        avisar("Usuario creado.");
      }
      setFormUsuario(null);
      await cargar();
    } catch (e) {
      fallo(e, "No se pudo guardar el usuario");
    } finally {
      setOcupado(false);
    }
  }

  async function toggleActivo(u: UsuarioAdmin) {
    try {
      await apiPut(`/usuarios/${u.id}`, { activo: !u.activo });
      await cargar();
    } catch (e) {
      fallo(e, "No se pudo cambiar el estado");
    }
  }

  async function resetPassword(u: UsuarioAdmin) {
    try {
      const r = await apiPost<{ password: string }>(`/usuarios/${u.id}/reset-password`, {});
      avisar(
        `Contraseña nueva de ${u.email}: ${r.password} — anotala ahora, no se vuelve a mostrar.`,
      );
    } catch (e) {
      fallo(e, "No se pudo resetear la contraseña");
    }
  }

  // ===== Roles y matriz =====

  function seleccionarRol(r: Rol) {
    setRolSel(r);
    setMatriz({ ...r.permisos });
    setNombreNuevoRol(null);
  }

  async function guardarMatriz() {
    if (!rolSel || ocupado) return;
    setOcupado(true);
    try {
      await apiPut(`/roles/${rolSel.id}/permisos`, { permisos: matriz });
      avisar(`Permisos de "${rolSel.nombre}" guardados. Rigen al próximo inicio de sesión.`);
      const nuevos = await cargar();
      setRolSel(nuevos.find((x) => x.id === rolSel.id) ?? null);
    } catch (e) {
      fallo(e, "No se pudieron guardar los permisos");
    } finally {
      setOcupado(false);
    }
  }

  async function crearRol(clonarDe: Rol | null) {
    const nombre = (nombreNuevoRol ?? "").trim();
    if (!nombre || ocupado) return;
    setOcupado(true);
    try {
      await apiPost("/roles", {
        nombre,
        clonar_de: clonarDe?.id ?? null,
        permisos: {},
      });
      avisar(clonarDe ? `Rol "${nombre}" clonado de "${clonarDe.nombre}".` : `Rol "${nombre}" creado.`);
      setNombreNuevoRol(null);
      const nuevos = await cargar();
      const creado = nuevos.find((x) => x.nombre === nombre && !x.es_sistema);
      if (creado) seleccionarRol(creado);
    } catch (e) {
      fallo(e, "No se pudo crear el rol");
    } finally {
      setOcupado(false);
    }
  }

  async function borrarRol(r: Rol) {
    try {
      await apiDelete(`/roles/${r.id}`);
      avisar(`Rol "${r.nombre}" eliminado.`);
      if (rolSel?.id === r.id) setRolSel(null);
      await cargar();
    } catch (e) {
      fallo(e, "No se pudo eliminar el rol");
    }
  }

  const matrizEditable = puedeEditar && rolSel !== null && !rolSel.es_sistema;

  return (
    <div className="config-card">
      <div className="seccion">Usuarios y permisos</div>
      <p className="config-ayuda">
        Cada usuario tiene un rol, y el rol define qué puede hacer por módulo (Ver ⊂ Editar ⊂
        Anular). Los roles de sistema no se editan: clonalos para ajustar la matriz. El nivel POS
        es independiente: define quién autoriza anulaciones en la caja.
      </p>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      {/* ===== Usuarios ===== */}
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Email</th>
              <th>Rol</th>
              <th>Nivel POS</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>
                  <b>{u.nombre}</b>
                </td>
                <td className="mono">{u.email}</td>
                <td>{rolNombre(u.rol_id)}</td>
                <td className="num">{u.nivel_acceso}</td>
                <td>
                  {u.activo ? "activo" : <span className="chip chip-anulado">inactivo</span>}
                </td>
                <td>
                  {puedeEditar && (
                    <>
                      <button
                        className="btn btn-ghost"
                        onClick={() =>
                          setFormUsuario({
                            id: u.id,
                            email: u.email,
                            nombre: u.nombre,
                            password: "",
                            rol_id: u.rol_id ?? "",
                            nivel_acceso: u.nivel_acceso,
                            activo: u.activo,
                          })
                        }
                      >
                        Editar
                      </button>{" "}
                      <button className="btn btn-ghost" onClick={() => void toggleActivo(u)}>
                        {u.activo ? "Desactivar" : "Activar"}
                      </button>{" "}
                      <button className="btn btn-ghost" onClick={() => void resetPassword(u)}>
                        Resetear clave
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {usuarios.length === 0 && (
              <tr>
                <td colSpan={6}>Cargando…</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {puedeEditar &&
        (formUsuario ? (
          <div className="pos-form-caja">
            <input
              className="input"
              placeholder="Email"
              value={formUsuario.email}
              disabled={formUsuario.id !== null}
              onChange={(e) => setFormUsuario({ ...formUsuario, email: e.target.value })}
            />
            <input
              className="input"
              placeholder="Nombre y apellido"
              value={formUsuario.nombre}
              onChange={(e) => setFormUsuario({ ...formUsuario, nombre: e.target.value })}
            />
            {formUsuario.id === null && (
              <input
                className="input"
                type="password"
                placeholder="Contraseña (mín. 6)"
                value={formUsuario.password}
                onChange={(e) => setFormUsuario({ ...formUsuario, password: e.target.value })}
              />
            )}
            <select
              className="input"
              value={formUsuario.rol_id}
              onChange={(e) => setFormUsuario({ ...formUsuario, rol_id: e.target.value })}
            >
              <option value="">Rol…</option>
              {roles
                .filter((r) => r.activo)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nombre}
                    {r.es_sistema ? "" : " (propio)"}
                  </option>
                ))}
            </select>
            <select
              className="input"
              value={formUsuario.nivel_acceso}
              onChange={(e) =>
                setFormUsuario({ ...formUsuario, nivel_acceso: Number(e.target.value) })
              }
            >
              {NIVELES_POS.map((n) => (
                <option key={n.valor} value={n.valor}>
                  {n.texto}
                </option>
              ))}
            </select>
            <div>
              <button
                className="btn btn-primary"
                disabled={
                  ocupado ||
                  !formUsuario.nombre.trim() ||
                  !formUsuario.rol_id ||
                  (formUsuario.id === null &&
                    (!formUsuario.email.trim() || formUsuario.password.length < 6))
                }
                onClick={() => void guardarUsuario()}
              >
                {formUsuario.id ? "Guardar" : "Crear usuario"}
              </button>{" "}
              <button className="btn btn-ghost" onClick={() => setFormUsuario(null)}>
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button className="btn btn-primary" onClick={() => setFormUsuario(USUARIO_VACIO)}>
            + Nuevo usuario
          </button>
        ))}

      {/* ===== Roles ===== */}
      <div className="seccion" style={{ marginTop: 24 }}>
        Roles
      </div>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Rol</th>
              <th>Tipo</th>
              <th className="num">Usuarios</th>
              <th>Permisos</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id} className={rolSel?.id === r.id ? "fila-sel" : undefined}>
                <td>
                  <b>{r.nombre}</b>
                  {!r.activo && <span className="chip chip-anulado"> inactivo</span>}
                </td>
                <td>{r.es_sistema ? "sistema" : "propio"}</td>
                <td className="num">{r.usuarios}</td>
                <td>
                  {Object.keys(r.permisos).length} módulo(s)
                </td>
                <td>
                  <button className="btn btn-ghost" onClick={() => seleccionarRol(r)}>
                    {r.es_sistema ? "Ver matriz" : "Editar matriz"}
                  </button>
                  {puedeEditar && !r.es_sistema && r.usuarios === 0 && (
                    <>
                      {" "}
                      <button className="btn btn-ghost" onClick={() => void borrarRol(r)}>
                        Eliminar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {puedeEditar &&
        (nombreNuevoRol !== null ? (
          <div className="pos-form-caja">
            <input
              className="input"
              placeholder="Nombre del rol (p. ej. Depósito)"
              value={nombreNuevoRol}
              autoFocus
              onChange={(e) => setNombreNuevoRol(e.target.value)}
            />
            <div>
              <button
                className="btn btn-primary"
                disabled={ocupado || !nombreNuevoRol.trim()}
                onClick={() => void crearRol(rolSel?.es_sistema ? rolSel : null)}
              >
                {rolSel?.es_sistema ? `Clonar "${rolSel.nombre}"` : "Crear rol vacío"}
              </button>{" "}
              <button className="btn btn-ghost" onClick={() => setNombreNuevoRol(null)}>
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button className="btn btn-primary" onClick={() => setNombreNuevoRol("")}>
            + Nuevo rol{rolSel?.es_sistema ? ` (clonar ${rolSel.nombre})` : ""}
          </button>
        ))}

      {/* ===== Matriz del rol seleccionado ===== */}
      {rolSel && catalogo && (
        <>
          <div className="seccion" style={{ marginTop: 24 }}>
            Matriz de permisos — {rolSel.nombre}
            {rolSel.es_sistema && (
              <span className="inicio-seccion-nota"> · rol de sistema (solo lectura)</span>
            )}
          </div>
          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Módulo</th>
                  <th>Sin acceso</th>
                  {catalogo.acciones.map((a) => (
                    <th key={a}>{ACCION_TEXTO[a] ?? a}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {catalogo.modulos.map((m) => {
                  const actual = matriz[m.codigo] ?? "";
                  return (
                    <tr key={m.codigo}>
                      <td>
                        <b>{m.nombre}</b>
                      </td>
                      {["", ...catalogo.acciones].map((a) => (
                        <td key={a || "sin"}>
                          <input
                            type="radio"
                            name={`perm-${m.codigo}`}
                            checked={actual === a}
                            disabled={!matrizEditable}
                            onChange={() => {
                              const nueva = { ...matriz };
                              if (a === "") delete nueva[m.codigo];
                              else nueva[m.codigo] = a;
                              setMatriz(nueva);
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {matrizEditable && (
            <button className="btn btn-primary" disabled={ocupado} onClick={() => void guardarMatriz()}>
              Guardar permisos
            </button>
          )}
        </>
      )}
    </div>
  );
}
