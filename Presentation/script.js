/* ==========================================================================
   Sua Consulta Presentation & Landing Page JavaScript
   Core Interactive Controllers
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    
    // Initialize Lucide Icons
    lucide.createIcons();

    /* --- DOM ELEMENTS --- */
    const body = document.body;
    const viewContainer = document.getElementById('viewContainer');
    const slideSections = document.querySelectorAll('.slide-section');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    
    // Mode Switchers
    const modeButtons = document.querySelectorAll('.mode-btn');
    
    // Slide Navigation Elements
    const presentationControls = document.getElementById('presentationControls');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const currentSlideLabel = document.getElementById('currentSlideLabel');
    
    // Presenter Notes
    const notesToggleBtn = document.getElementById('notesToggleBtn');
    const notesDrawer = document.getElementById('notesDrawer');
    const notesCloseBtn = document.getElementById('notesCloseBtn');
    const speechScriptContent = document.getElementById('speechScriptContent');
    
    // Landing Mode Sidebar Nav
    const landingNav = document.getElementById('landingNav');
    const landingNavLinks = document.querySelectorAll('.landing-nav a');

    /* --- STATE MANAGEMENT --- */
    let currentSlide = 1;
    const totalSlides = slideSections.length;
    let isNotesOpen = false;
    let currentMode = 'presentation'; // 'presentation' or 'landing'

    /* ==========================================================================
       THEMING LOGIC
       ========================================================================== */
    themeToggleBtn.addEventListener('click', () => {
        if (body.classList.contains('dark-theme')) {
            body.classList.remove('dark-theme');
            body.classList.add('light-theme');
        } else {
            body.classList.remove('light-theme');
            body.classList.add('dark-theme');
        }
    });

    /* ==========================================================================
       VIEW MODE CONTROLLER (PRESENTATION vs LANDING)
       ========================================================================== */
    function switchMode(newMode) {
        currentMode = newMode;
        
        // Update Selector Buttons
        modeButtons.forEach(btn => {
            if (btn.getAttribute('data-mode') === newMode) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        if (newMode === 'presentation') {
            body.classList.remove('landing-mode');
            body.classList.add('presentation-mode');
            
            // Re-align slide layouts
            slideSections.forEach(section => {
                const slideNum = parseInt(section.getAttribute('data-slide'));
                if (slideNum === currentSlide) {
                    section.classList.add('active');
                } else {
                    section.classList.remove('active');
                }
            });
            
            // Sync speech script drawer
            updateSpeechNotes();
            
        } else if (newMode === 'landing') {
            body.classList.remove('presentation-mode');
            body.classList.add('landing-mode');
            
            // Ensure notes drawer is closed
            notesDrawer.classList.remove('open');
            isNotesOpen = false;
            
            // Make all sections visible for scrolling
            slideSections.forEach(section => {
                section.classList.remove('active'); // CSS handles display when in landing-mode
            });
            
            // Scroll to the active slide's section
            const targetSection = document.getElementById(`slide${currentSlide}`);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-mode');
            switchMode(mode);
        });
    });

    /* ==========================================================================
       PRESENTATION SLIDES ENGINE
       ========================================================================== */
    function goToSlide(slideIndex) {
        if (slideIndex < 1 || slideIndex > totalSlides) return;
        
        // Remove active class from old slide
        const oldSlide = document.querySelector(`.slide-section[data-slide="${currentSlide}"]`);
        if (oldSlide) oldSlide.classList.remove('active');
        
        currentSlide = slideIndex;
        
        // Add active class to new slide
        const newSlide = document.querySelector(`.slide-section[data-slide="${currentSlide}"]`);
        if (newSlide) newSlide.classList.add('active');
        
        // Update Controls Label
        currentSlideLabel.textContent = currentSlide;
        
        // Sync Speech notes
        updateSpeechNotes();
    }

    function updateSpeechNotes() {
        const activeSlide = document.querySelector(`.slide-section[data-slide="${currentSlide}"]`);
        if (activeSlide) {
            const scriptElement = activeSlide.querySelector('.speech-script');
            if (scriptElement) {
                speechScriptContent.innerHTML = scriptElement.innerHTML;
            } else {
                speechScriptContent.textContent = "Nenhuma nota de fala para este slide.";
            }
        }
    }

    // Nav Listeners
    prevBtn.addEventListener('click', () => goToSlide(currentSlide - 1));
    nextBtn.addEventListener('click', () => goToSlide(currentSlide + 1));

    // Keyboard Arrow Keys support
    document.addEventListener('keydown', (e) => {
        if (currentMode !== 'presentation') return;
        
        if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
            goToSlide(currentSlide - 1);
        } else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
            goToSlide(currentSlide + 1);
        }
    });

    // Notes drawer toggle
    notesToggleBtn.addEventListener('click', () => {
        isNotesOpen = !isNotesOpen;
        if (isNotesOpen) {
            notesDrawer.classList.add('open');
        } else {
            notesDrawer.classList.remove('open');
        }
    });

    notesCloseBtn.addEventListener('click', () => {
        notesDrawer.classList.remove('open');
        isNotesOpen = false;
    });

    /* ==========================================================================
       LANDING PAGE SCROLL SPY & SIDE NAV
       ========================================================================== */
    // ScrollSpy observer
    const observerOptions = {
        root: null,
        rootMargin: '-30% 0px -40% 0px',
        threshold: 0
    };

    const scrollSpyObserver = new IntersectionObserver((entries) => {
        if (currentMode !== 'landing') return;
        
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const slideNum = parseInt(entry.target.getAttribute('data-slide'));
                currentSlide = slideNum;
                
                // Highlight Sidebar navigation item
                landingNavLinks.forEach(link => {
                    const linkSlide = parseInt(link.getAttribute('data-slide'));
                    if (linkSlide === currentSlide) {
                        link.classList.add('active');
                    } else {
                        link.classList.remove('active');
                    }
                });
            }
        });
    }, observerOptions);

    slideSections.forEach(section => {
        scrollSpyObserver.observe(section);
    });

    // Landing nav click listeners
    landingNavLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const slideNum = parseInt(link.getAttribute('data-slide'));
            currentSlide = slideNum;
            
            const targetSection = document.getElementById(`slide${slideNum}`);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });


    /* ==========================================================================
       WIDGET 1: LATENCY SIMULATOR ENGINE (WhatsApp -> API -> FCM -> Flutter)
       ========================================================================== */
    const btnTriggerLatencySim = document.getElementById('btnTriggerLatencySim');
    const latencyTimer = document.getElementById('latencyTimer');
    const simIsisResponse = document.getElementById('simIsisResponse');
    const nodeWebhook = document.getElementById('nodeWebhook');
    const nodeFCM = document.getElementById('nodeFCM');
    const simParticle = document.getElementById('simParticle');
    const noApptsPlaceholder = document.getElementById('noApptsPlaceholder');
    const apptCardSim = document.getElementById('apptCardSim');
    const simStatusText = document.getElementById('simStatusText');
    const simChatArea = document.getElementById('simChatArea');

    let simInterval = null;
    let startTime = null;

    btnTriggerLatencySim.addEventListener('click', () => {
        // Prevent double click
        btnTriggerLatencySim.disabled = true;
        
        // Reset States
        latencyTimer.textContent = "0.00s";
        simIsisResponse.classList.remove('show');
        nodeWebhook.classList.remove('pulse');
        nodeFCM.classList.remove('pulse');
        simParticle.classList.remove('moving');
        noApptsPlaceholder.style.display = 'block';
        apptCardSim.classList.remove('show');
        simStatusText.innerHTML = "<span style='color: var(--accent-blue)'>Iniciando processamento assíncrono...</span>";
        
        // 1. Start Stopwatch
        startTime = performance.now();
        simInterval = setInterval(() => {
            const delta = (performance.now() - startTime) / 1000;
            latencyTimer.textContent = `${delta.toFixed(2)}s`;
        }, 10);
        
        // 2. WhatsApp Bubble pops up
        setTimeout(() => {
            simIsisResponse.classList.add('show');
            simChatArea.scrollTop = simChatArea.scrollHeight;
            simStatusText.textContent = "Transcrição e moderação ativa rodando no Backend...";
        }, 300);
        
        // 3. Webhook Pulsing & Particle Moving
        setTimeout(() => {
            nodeWebhook.classList.add('pulse');
            simParticle.classList.add('moving');
            simStatusText.textContent = "Inserindo dados estruturados no PostgreSQL e acionando FCM...";
        }, 600);

        // 4. FCM Pulsing
        setTimeout(() => {
            nodeFCM.classList.add('pulse');
            simStatusText.textContent = "Disparando notificação Push em segundo plano...";
        }, 1100);

        // 5. Appears in Doctor Flutter App
        setTimeout(() => {
            noApptsPlaceholder.style.display = 'none';
            apptCardSim.classList.add('show');
            
            // Stop stopwatch at realistic sub-2s time
            clearInterval(simInterval);
            const totalDuration = (performance.now() - startTime) / 1000;
            latencyTimer.textContent = `${totalDuration.toFixed(2)}s`;
            
            simStatusText.innerHTML = `✅ <strong style="color: var(--success-green)">SUCESSO PONT-A-PONTA!</strong> Dados sincronizados em <strong>${totalDuration.toFixed(2)}s</strong> via Firebase Cloud Messaging!`;
            
            // Re-enable button after cooldown
            setTimeout(() => {
                btnTriggerLatencySim.disabled = false;
            }, 1500);
            
        }, 1250 + Math.random() * 200); // Dynamic latency finish under 2s (approx 1.25s to 1.45s)
    });


    /* ==========================================================================
       WIDGET 2: CONTENT MODERATION SANDBOX
       ========================================================================== */
    const modSimBtns = document.querySelectorAll('.mod-sim-btn');
    const customModInput = document.getElementById('customModInput');
    const btnTestMod = document.getElementById('btnTestMod');
    const modStatusBadge = document.getElementById('modStatusBadge');
    const modDbValue = document.getElementById('modDbValue');

    function runModerationCheck(text, forcedType = null) {
        let type = forcedType;
        
        // Simple heuristic for custom typed words
        if (!type) {
            const lowerText = text.toLowerCase();
            const badWords = ['hack', 'virus', 'spam', 'roubo', 'farsa', 'dinheiro', 'porn', 'sex', 'mata', 'golpe', 'ilícito'];
            const medicalWords = ['dipirona', 'mancha', 'coceira', 'dor', 'consulta', 'pele', 'dr', 'carlos', 'medicina', 'remédio', 'receita', 'exame'];
            
            let hasBad = badWords.some(w => lowerText.includes(w));
            let hasMed = medicalWords.some(w => lowerText.includes(w));
            
            if (hasBad) {
                type = 'harmful';
            } else if (hasMed) {
                type = 'clinical';
            } else {
                type = 'allowed-standard';
            }
        }

        // Animate processing
        modStatusBadge.textContent = "Analisando...";
        modStatusBadge.className = "result-badge";
        modDbValue.textContent = "Processando no PostgreSQL...";
        modDbValue.className = "result-db-value";

        setTimeout(() => {
            if (type === 'clinical') {
                modStatusBadge.textContent = "🩺 CLINICAL EXCEPTION (ALLOWED)";
                modStatusBadge.classList.add('clinical');
                modDbValue.textContent = text.substring(0, 50) + (text.length > 50 ? '...' : '');
            } else if (type === 'clinical-prescription') {
                modStatusBadge.textContent = "💊 MEDICAL TERM (ALLOWED)";
                modStatusBadge.classList.add('clinical');
                modDbValue.textContent = text;
            } else if (type === 'harmful') {
                modStatusBadge.textContent = "❌ THREAT BLOCKED (CENSORED)";
                modStatusBadge.classList.add('blocked');
                modDbValue.textContent = "[MENSAGEM BLOQUEADA PELO FILTRO DE SEGURANÇA]";
                modDbValue.classList.add('red-alert');
            } else {
                modStatusBadge.textContent = "✅ TEXT (ALLOWED)";
                modStatusBadge.classList.add('clinical');
                modDbValue.textContent = text;
            }
        }, 400);
    }

    modSimBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.getAttribute('data-text');
            const type = btn.getAttribute('data-type');
            customModInput.value = text;
            runModerationCheck(text, type);
        });
    });

    btnTestMod.addEventListener('click', () => {
        const text = customModInput.value.trim();
        if (text) {
            runModerationCheck(text);
        }
    });

    // Trigger check on enter key in input
    customModInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const text = customModInput.value.trim();
            if (text) runModerationCheck(text);
        }
    });


    /* ==========================================================================
       WIDGET 3: MULTI-AGENT GRAPH PLAYGROUND
       ========================================================================== */
    const satNodes = document.querySelectorAll('.sat-node');
    const agentDetailPanel = document.getElementById('agentDetailPanel');
    const agentOrchestrator = document.getElementById('agentOrchestrator');

    const agentData = {
        backend: {
            title: "develop-fastapi-backend",
            role: "Codificação do Motor de API Assíncrona",
            desc: "Agente responsável por programar endpoints RESTful assíncronos no FastAPI, gerenciar webhooks da Meta API, estruturar schemas de entrada Pydantic e implementar background task pools.",
            code: `# FastAPI Async Webhook router
@router.post("/webhook")
async def handle_whatsapp_incoming(
    payload: WhatsAppPayload,
    background_tasks: BackgroundTasks
):
    # Interceptação e enfileiramento assíncrono
    background_tasks.add_task(process_message_pipeline, payload)
    return {"status": "event_received_queued"}`
        },
        db: {
            title: "database-architect",
            role: "Estruturação Relacional & Migrações",
            desc: "Agente responsável por criar as tabelas do PostgreSQL via SQLAlchemy, gerenciar indexação acelerada de chaves estrangeiras, realizar backups e manter integridade LGPD clínica.",
            code: `# Patient Table schema with security constraints
class PatientModel(Base):
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone_number = Column(String(20), unique=True, index=True)
    full_name = Column(String(100), nullable=False)
    clinical_history = Column(Text, default="[MENSAGEM INICIALIZADA]")`
        },
        frontend: {
            title: "flutter-frontend-agent",
            role: "Construção de Telas & Design System",
            desc: "Agente especialista na geração de widgets em Flutter Mobile/Web. Constrói componentes Material 3 altamente modulares sob as diretrizes oficiais de Clean UI e cores do Design System.",
            code: `// Widget da Agenda Inteligente (Material 3)
class AppointmentCard extends StatelessWidget {
  final Appointment appt;
  
  const AppointmentCard({Key? key, required this.appt}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: AppTheme.surfaceWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24.0), // Pill layout
      ),
      child: ListTile(...)
    );
  }
}`
        },
        qa: {
            title: "qa-test-engineer",
            role: "Engenharia de Qualidade & Testes",
            desc: "Agente encarregado de escrever testes unitários assíncronos (pytest-asyncio), conduzir testes de estresse em chamados webhook concorrentes e auditar contratos de segurança.",
            code: `# Integration unit test for Latency Pipeline
@pytest.mark.asyncio
async def test_webhook_latency_threshold():
    start = time.perf_counter()
    response = await client.post("/webhook", json=mock_payload)
    end = time.perf_counter()
    
    assert response.status_code == 200
    assert (end - start) < 0.200 # API responde < 200ms`
        }
    };

    function selectAgentNode(node) {
        // Remove active class from all satellites
        satNodes.forEach(n => n.classList.remove('active'));
        
        node.classList.add('active');
        const agentKey = node.getAttribute('data-agent');
        const data = agentData[agentKey];
        
        if (data) {
            agentDetailPanel.innerHTML = `
                <h4>🤖 Agente: ${data.title}</h4>
                <p><strong>Atribuição:</strong> ${data.role}</p>
                <p>${data.desc}</p>
                <pre class="agent-code-block"><code>${escapeHTML(data.code)}</code></pre>
            `;
        }
    }

    satNodes.forEach(node => {
        node.addEventListener('click', () => {
            selectAgentNode(node);
        });
    });

    if (agentOrchestrator) {
        agentOrchestrator.addEventListener('click', () => {
            // Highlight all
            satNodes.forEach(n => n.classList.add('active'));
            agentDetailPanel.innerHTML = `
                <h4>🧠 Orquestrador Central Multiagente</h4>
                <p><strong>Arquivo de IP:</strong> <code>orchestrate-omniconnect.md</code></p>
                <p>Atua como o engenheiro-gerente autônomo. Ele traduz especificações escritas em Markdown, divide os épicos em tarefas técnicas (FastAPI, Flutter widgets, schemas, scripts de teste) e delega para os agentes especialistas correspondentes no registry, validando saídas em loops autorreguláveis.</p>
                <div style="margin-top:0.8rem; font-size: 0.8rem; color: var(--accent-blue)">
                    ⚡ Velocidade de entrega 5x maior que times analógicos.
                </div>
            `;
        });
    }

    // Helper to escape HTML tags in code blocks
    function escapeHTML(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }


    /* ==========================================================================
       WIDGET 4: RAG ANTI-HALLUCINATION PROTOCOL (new_session: true)
       ========================================================================== */
    const btnResetSession = document.getElementById('btnResetSession');
    const memoryLogs = document.getElementById('memoryLogs');
    const ragStatusText = document.getElementById('ragStatusText');

    btnResetSession.addEventListener('click', () => {
        btnResetSession.disabled = true;
        
        // Trigger wipe animation
        memoryLogs.style.opacity = '0.3';
        ragStatusText.innerHTML = "🌀 <strong style='color: var(--warning-orange)'>Sinalizando Backend: new_session=true...</strong>";
        
        setTimeout(() => {
            // Repopulate memory clean
            memoryLogs.innerHTML = `
                <div class="log-item" style="color: var(--success-green)">[SYSTEM]: Memory Saver reset completed. State cleared.</div>
                <div class="log-item">[SYSTEM]: Role = Isis Assistant (Triagem de Entrada)</div>
                <div class="log-item" style="color: var(--accent-blue)">[INFO]: Memória limpa de contaminações retroativas. Risco de alucinação zerado.</div>
            `;
            memoryLogs.style.opacity = '1';
            ragStatusText.innerHTML = "✅ <strong style='color: var(--success-green)'>PROTOCOLO DE RESET ATIVADO!</strong> Memória conversacional antiga foi completamente isolada. Próxima resposta terá contexto 100% limpo.";
            
            setTimeout(() => {
                btnResetSession.disabled = false;
            }, 1000);
        }, 1000);
    });


    /* ==========================================================================
       WIDGET 5: INTERACTIVE SVG FINANCIAL CHART TOOLTIP
       ========================================================================== */
    const chartDots = document.querySelectorAll('.chart-dot');
    const chartTooltip = document.getElementById('chartTooltip');

    if (chartTooltip && chartDots.length > 0) {
        chartDots.forEach(dot => {
            dot.addEventListener('mouseenter', (e) => {
                const val = dot.getAttribute('data-val');
                const week = dot.nextElementSibling || { textContent: 'Faturamento' };
                chartTooltip.innerHTML = `📈 <strong>Faturamento: ${val}</strong>`;
                chartTooltip.style.borderColor = "var(--accent-blue)";
                chartTooltip.style.background = "rgba(10, 65, 116, 0.4)";
            });
            
            dot.addEventListener('mouseleave', () => {
                chartTooltip.innerHTML = "Passe o mouse nos pontos para ver o valor";
                chartTooltip.style.borderColor = "var(--border-color)";
                chartTooltip.style.background = "rgba(0,0,0,0.3)";
            });
        });
    }

    // Initialize Presentation on load
    goToSlide(1);
});
