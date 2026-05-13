const codigoPenalData = [
    {
        id: "disposiciones",
        title: "Disposiciones Generales",
        icon: "fas fa-balance-scale",
        content: `
            <p><strong>Para evitar vacíos legales:</strong></p>
            <ul>
                <li><strong>Acumulación de cargos:</strong> Si un jugador comete múltiples delitos a la vez (ej. huir de la policía, chocar y tener armas ilegales), las multas y los tiempos de cárcel se suman.</li>
                <li><strong>Complicidad:</strong> Todo aquel que ayude, conduzca el vehículo de escape o encubra un delito, recibirá la misma condena que el autor principal.</li>
                <li><strong>Zonas Seguras (Safezones):</strong> Cometer cualquier delito mayor dentro de una zona segura (Spawn, Hospital) duplica la multa y la condena, además de ser motivo de Kick/Ban administrativo.</li>
            </ul>
        `
    },
    {
        id: "art1",
        title: "Artículo 1: Exceso de Velocidad / Conducción Temeraria",
        icon: "fas fa-tachometer-alt",
        content: `
            <p><strong>Delito:</strong> Conducir por encima del límite establecido o de forma que ponga en riesgo a los civiles.</p>
            <p><strong>Multa:</strong> $1,500 MXN</p>
            <p><strong>Cárcel:</strong> 0 segundos (Solo multa).</p>
            <p><strong>Sanción Adicional:</strong> Si es reincidente (3ra vez), se le incauta el vehículo al corralón.</p>
        `
    },
    {
        id: "art2",
        title: "Artículo 2: Estacionamiento Ilegal o Abandono de Vehículo",
        icon: "fas fa-parking",
        content: `
            <p><strong>Delito:</strong> Dejar el vehículo bloqueando el tráfico o en zonas exclusivas (ej. entrada de comisaría).</p>
            <p><strong>Multa:</strong> $800 MXN</p>
            <p><strong>Cárcel:</strong> 0 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Remolque inmediato del vehículo (Grúa).</p>
        `
    },
    {
        id: "art3",
        title: "Artículo 3: Evasión de Tránsito (Fuga nivel 1)",
        icon: "fas fa-running",
        content: `
            <p><strong>Delito:</strong> No detenerse ante las sirenas o indicaciones de un oficial de policía de manera inmediata.</p>
            <p><strong>Multa:</strong> $5,000 MXN</p>
            <p><strong>Cárcel:</strong> 120 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Incautación del vehículo usado para la fuga.</p>
        `
    },
    {
        id: "art4",
        title: "Artículo 4: Conducción de Vehículo Robado",
        icon: "fas fa-car-crash",
        content: `
            <p><strong>Delito:</strong> Ser sorprendido conduciendo un vehículo que ha sido reportado como robado (GTA).</p>
            <p><strong>Multa:</strong> $12,000 MXN</p>
            <p><strong>Cárcel:</strong> 250 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Retiro absoluto del vehículo y decomiso de ganzúas o herramientas de robo.</p>
        `
    },
    {
        id: "art5",
        title: "Artículo 5: Alteración del Orden / Escándalo en Vía Pública",
        icon: "fas fa-volume-up",
        content: `
            <p><strong>Delito:</strong> Gritar, insultar sin motivo de rol justificado, o iniciar peleas a puñetazos en la calle.</p>
            <p><strong>Multa:</strong> $2,500 MXN</p>
            <p><strong>Cárcel:</strong> 60 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Ninguna.</p>
        `
    },
    {
        id: "art6",
        title: "Artículo 6: Desacato a la Autoridad",
        icon: "fas fa-user-shield",
        content: `
            <p><strong>Delito:</strong> Negarse a mostrar identificación, no acatar órdenes directas de la policía, o entorpecer una escena del crimen.</p>
            <p><strong>Multa:</strong> $4,000 MXN</p>
            <p><strong>Cárcel:</strong> 150 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Cateo (revisión de inventario) obligatorio por comportamiento sospechoso.</p>
        `
    },
    {
        id: "art7",
        title: "Artículo 7: Vandalismo y Daño a la Propiedad",
        icon: "fas fa-hammer",
        content: `
            <p><strong>Delito:</strong> Destruir semáforos, chocar intencionalmente patrullas o dañar propiedad privada.</p>
            <p><strong>Multa:</strong> $5,000 MXN (para cubrir reparaciones).</p>
            <p><strong>Cárcel:</strong> 120 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Retiro de herramientas usadas para el daño (bates, palancas, etc.).</p>
        `
    },
    {
        id: "art8",
        title: "Artículo 8: Posesión de Armas sin Licencia (Nivel 1)",
        icon: "fas fa-hand-paper",
        content: `
            <p><strong>Delito:</strong> Portar armas de fuego cortas sin el permiso correspondiente del servidor.</p>
            <p><strong>Multa:</strong> $10,000 MXN</p>
            <p><strong>Cárcel:</strong> 200 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Decomiso total del arma y munición.</p>
        `
    },
    {
        id: "art9",
        title: "Artículo 9: Portación de Armamento Pesado / Exclusivo",
        icon: "fas fa-crosshairs",
        content: `
            <p><strong>Delito:</strong> Portar rifles de asalto, escopetas o armas largas en vía pública, tengan o no licencia (salvo en roles específicos).</p>
            <p><strong>Multa:</strong> $25,000 MXN</p>
            <p><strong>Cárcel:</strong> 400 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Decomiso de todas las armas del inventario y revocación permanente de la licencia de armas.</p>
        `
    },
    {
        id: "art10",
        title: "Artículo 10: Robo a Mano Armada",
        icon: "fas fa-mask",
        content: `
            <p><strong>Delito:</strong> Usar la fuerza o armas para despojar a un jugador de su dinero o asaltar gasolineras/tiendas pequeñas.</p>
            <p><strong>Multa:</strong> $15,000 MXN</p>
            <p><strong>Cárcel:</strong> 300 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Decomiso de armas, retiro del dinero robado y confiscación del vehículo de escape.</p>
        `
    },
    {
        id: "art11",
        title: "Artículo 11: Robo al Banco o Joyería",
        icon: "fas fa-gem",
        content: `
            <p><strong>Delito:</strong> Participación directa o indirecta en el asalto a las bóvedas de la ciudad.</p>
            <p><strong>Multa:</strong> $50,000 MXN</p>
            <p><strong>Cárcel:</strong> 600 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Confiscación de todo el dinero sucio, decomiso de todas las armas y herramientas (taladros, bolsas), y pérdida del vehículo.</p>
        `
    },
    {
        id: "art12",
        title: "Artículo 12: Intento de Homicidio / Agresión a un Oficial",
        icon: "fas fa-skull-crossbones",
        content: `
            <p><strong>Delito:</strong> Disparar o intentar abatir a cualquier oficial de policía, sheriff o personal de emergencias (Bomberos/Médicos).</p>
            <p><strong>Multa:</strong> $40,000 MXN</p>
            <p><strong>Cárcel:</strong> 500 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Decomiso absoluto de inventario (armas, municiones).</p>
        `
    },
    {
        id: "art13",
        title: "Artículo 13: Homicidio Calificado (RDM)",
        icon: "fas fa-user-slash",
        content: `
            <p><strong>Delito:</strong> Abatir a un civil o policía con premeditación (debe estar justificado con rol. Si es asesinato al azar -RDM-, pasa directo a la administración).</p>
            <p><strong>Multa:</strong> $75,000 MXN</p>
            <p><strong>Cárcel:</strong> 800 segundos (o el máximo que permita tu servidor).</p>
            <p><strong>Sanción Adicional:</strong> Limpieza total de inventario ilegal, confiscación de vehículos implicados. Si el homicidio se hizo sin rol previo, es motivo de baneo o jail administrativo.</p>
        `
    },
    {
        id: "art14",
        title: "Artículo 14: Secuestro de Civiles o Autoridades",
        icon: "fas fa-user-lock",
        content: `
            <p><strong>Delito:</strong> Privar de la libertad a otro jugador en contra de su voluntad para pedir rescate o hacer daño.</p>
            <p><strong>Multa:</strong> $60,000 MXN</p>
            <p><strong>Cárcel:</strong> 650 segundos.</p>
            <p><strong>Sanción Adicional:</strong> Confiscación de todos los vehículos involucrados, armas y dinero en efectivo.</p>
        `
    }
];
