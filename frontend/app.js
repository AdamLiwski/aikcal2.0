let pristineRecipeData = null;

document.addEventListener('DOMContentLoaded', () => {

    // === STAN APLIKACJI ===
    const state = {
        token: localStorage.getItem('token'),
        currentUser: null,
        currentDate: new Date(), // Data aktualnie wyświetlana w dzienniku
        activeView: 'dashboard',
        isLoading: false,
        isListening: false,
        summary: null,
        analysis: {
            aiSummary: null,
            generatedAt: null,
            startDate: null,
            endDate: null,
        },
        analysisRange: {
            startDate: null,
            endDate: null,
            data: null,
        },
        social: {
            friends: [],
            requests: [],
            searchResults: []
            // Usunęliśmy 'challenges', ponieważ będą teraz częścią stanu 'social' pobieranego dynamicznie
        },
        chat: { // NOWY OBIEKT DLA OBSŁUGI WIELU ROZMÓW
            conversations: [], // Lista wszystkich rozmów
            activeConversationId: null, // ID aktualnie otwartej rozmowy
            messages: [] // Wiadomości dla aktywnej rozmowy
        },
        enums: {
            MealCategory: ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"],
            DietStyle: ["Zbilansowana", "Ketogeniczna", "Wegetariańska", "Niskowęglowodanowa", "Wysokobiałkowa"],
            ActivityLevel: ["BMR", "Siedzący", "Lekka aktywność", "Umiarkowana aktywność", "Aktywny", "Bardzo aktywny"],
            Gender: ["Mężczyzna", "Kobieta"],
            // NOWE ENUMY ZGODNE Z BACKENDEM
            SubscriptionStatus: ["free", "premium"],
            ProductState: ["solid", "liquid"]
        },
        calorieAlerts: [
            "Osiągnąłeś już swój cel kaloryczny na dziś. Czy na pewno chcesz dodać ten posiłek?",
            "Twój dzienny cel jest już zrealizowany. Czasem warto posłuchać swojego ciała – czy to głód, czy tylko zachcianka?",
            "Przekraczasz swój limit. Pamiętaj, że każdy wybór ma znaczenie. Czy na pewno kontynuować?",
            "Cel osiągnięty! Jeśli to kolejny posiłek, upewnij się, że to świadoma decyzja. Dodać mimo to?"
        ],
        // --- DODAJ TEN NOWY OBIEKT ---
        userLimits: {
            photoAnalysis: 0,
            textAnalysis: 0,
            chatMessages: 0,
            weeklyAnalysis: 0,
            aiChef: 0
        }
        // --- KONIEC NOWEGO OBIEKTU ---
    };

    // === SELEKTORY DOM ===
    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => document.querySelectorAll(selector);

    const selectors = {
        appContainer: $('#app-container'),
        authContainer: $('#auth-container'),
        loader: $('#loader'),
        notificationBar: $('#notification-bar'),
        mainContent: $('#main-content'),
        loginForm: $('#login-form'),
        registerForm: $('#register-form'),
        showRegister: $('#show-register'),
        showLogin: $('#show-login'),
        authError: $('#auth-error'),
        settingsModal: $('#settings-modal'),
        calendarModal: $('#calendar-modal'),
        addMealModal: $('#add-meal-modal'),
        detailsModal: $('#details-modal'),
        analysisStartDate: $('#analysis-start-date'),
        analysisEndDate: $('#analysis-end-date'),
        generateAnalysisBtn: $('#generate-analysis-btn'),
        aiCoachContainer: $('#ai-coach-container'),
        aiCoachSummary: $('#ai-coach-summary'),
        macroChartContainer: $('#macro-chart-container'),
        weightChartContainer: $('#weight-chart-container'),
        workoutsSummaryContainer: $('#workouts-summary-container'),
        totalWorkouts: $('#total-workouts'),
        totalCaloriesBurned: $('#total-calories-burned'),
        editMealEntryModal: $('#edit-meal-entry-modal'), // NOWE: Modal do edycji wpisu
    };

    // === USŁUGI API ===
    const api = {
        baseUrl: '/api',
        async request(endpoint, options = {}) {
            const headers = { 'Content-Type': 'application/json', ...options.headers };
            if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

            setLoading(true);
            try {
                const response = await fetch(this.baseUrl + endpoint, { ...options, headers });
                if (response.status === 204) return true;

                const contentType = response.headers.get('content-type');
                if (!response.ok) {
                    let errorDetail = `Błąd serwera: ${response.status} ${response.statusText}`;
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorDetail = errorData.detail || JSON.stringify(errorData);
                    }
                    throw new Error(errorDetail);
                }
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                }
                return true;
            } catch (error) {
                if (String(error.message).includes('401') && state.token) {
                    handle.logout();
                } else {
                    showNotification(error.message, 'error');
                }
                throw error;
            } finally {
                setLoading(false);
            }
        },
        // --- Uwierzytelnianie i Użytkownik ---
        login: (email, password) => {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);
            return api.request('/users/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
        },
        register: (email, password) => api.request('/users/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
        getMe: () => api.request('/users/me'),
        updateMe: (data) => api.request('/users/me', { method: 'PUT', body: JSON.stringify(data) }),
        deleteMe: () => api.request('/users/me', { method: 'DELETE' }),

        // --- Nowe Akcje Uwierzytelniające ---
        requestPasswordReset: (email) => api.request('/auth/request-password-reset', { method: 'POST', body: JSON.stringify({ email }) }),
        resetPassword: (token, new_password) => api.request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password }) }),

        // --- Analiza ---
        analyze: (data) => api.request('/analysis/meal', { method: 'POST', body: JSON.stringify(data) }),
        getDietPlan: () => api.request('/analysis/suggest-diet-plan'),
        suggestGoals: (data) => api.request('/users/suggest-goals', { method: 'POST', body: JSON.stringify(data) }),
        getLatestAnalysis: () => api.request('/analysis/latest'),
        generateWeeklyAnalysis: (startDate, endDate) => api.request('/analysis/generate', { method: 'POST', body: JSON.stringify({ start_date: startDate, end_date: endDate }) }),
        
        // --- Dziennik ---
        getSummaryByDate: (date) => api.request(`/summary/${date}?cb=${new Date().getTime()}`), // Dodano cache-busting
        createMeal: (mealData) => api.request('/meals', { method: 'POST', body: JSON.stringify(mealData) }),
        addMealEntry: (mealId, entryData) => api.request(`/meals/${mealId}/entries`, { method: 'POST', body: JSON.stringify(entryData) }),
        updateMealEntry: (entryId, entryData) => api.request(`/meals/entries/${entryId}`, { method: 'PUT', body: JSON.stringify(entryData) }),
        deleteMealEntry: (entryId) => api.request(`/meals/entries/${entryId}`, { method: 'DELETE' }),
        addWater: (data) => api.request('/water', { method: 'POST', body: JSON.stringify(data) }),
        deleteWater: (entryId) => api.request(`/water/${entryId}`, { method: 'DELETE' }),
        addWorkout: (data) => api.request('/workouts', { method: 'POST', body: JSON.stringify(data) }),
        deleteWorkout: (workoutId) => api.request(`/workouts/${workoutId}`, { method: 'DELETE' }),

        // --- Nowy Czat ---
        getConversations: () => api.request('/chat/conversations'),
        createConversation: () => api.request('/chat/conversations', { method: 'POST' }),
        getConversationMessages: (convoId) => api.request(`/chat/conversations/${convoId}`),
        sendMessageToConversation: (convoId, message) => api.request(`/chat/conversations/${convoId}/messages`, { method: 'POST', body: JSON.stringify({ message }) }),
        pinConversation: (convoId) => api.request(`/chat/conversations/${convoId}/pin`, { method: 'POST' }),
        deleteConversation: (convoId) => api.request(`/chat/conversations/${convoId}`, { method: 'DELETE' }),

        // --- Społeczność ---
        searchUsers: (email) => api.request(`/social/users/search?email=${encodeURIComponent(email)}`),
        sendFriendRequest: (friendId) => api.request('/social/friends/request', { method: 'POST', body: JSON.stringify({ friend_id: friendId }) }),
        getFriendRequests: () => api.request('/social/friends/requests'),
        respondToRequest: (friendshipId, status) => api.request(`/social/friends/requests/${friendshipId}/respond?status=${status}`, { method: 'POST' }),
        getFriends: () => api.request('/social/friends'),
        deleteFriend: (friendId) => api.request(`/social/friends/${friendId}`, { method: 'DELETE' }),
        getChallenges: () => api.request('/challenges'),
        getMyChallenges: () => api.request('/challenges/me'),
        joinChallenge: (challengeId) => api.request(`/challenges/${challengeId}/join`, { method: 'POST' }),
    };

    // === TEMPLATKI HTML (bez zmian) ===
    const templates = {
        // Usunięto hardkodowany link Google OAuth z authBox
        authBox: `
            <div class="auth-box">
                <h3 id="auth-title">Zaloguj się</h3>
                <form id="login-form">
                    <input type="email" id="login-email" placeholder="Email" required>
                    <input type="password" id="login-password" placeholder="Hasło" required>
                    <button type="submit" class="primary-btn">Zaloguj</button>
                    <a href="#" id="show-forgot-password" class="forgot-password-link">Nie pamiętasz hasła?</a>
                </form>
                <form id="register-form" class="hidden">
                    <input type="email" id="register-email" placeholder="Email" required>
                    <input type="password" id="register-password" placeholder="Hasło" required>
                    <div class="form-group-inline">
                        <input type="checkbox" id="register-terms" required>
                        <label for="register-terms">Akceptuję <a href="/regulamin.html" target="_blank">Regulamin</a> i <a href="/polityka-prywatnosci.html" target="_blank">Politykę Prywatności</a>.</label>
                    </div>
                    <button type="submit" class="primary-btn">Zarejestruj</button>
                </form>
                <form id="forgot-password-form" class="hidden">
                    <p>Wpisz swój adres e-mail, a wyślemy Ci link do zresetowania hasła.</p>
                    <input type="email" id="forgot-email" placeholder="Email" required>
                    <button type="submit" class="primary-btn">Wyślij link</button>
                </form>
                <div class="or-divider"><span>LUB</span></div>
                <div id="google-login-placeholder"></div>
                <p id="auth-error" class="error-message"></p>
                <p id="auth-switch" class="auth-switch">Nie masz konta? <a href="#" id="show-register">Zarejestruj się</a></p>
            </div>
        `,
        dashboardView: `
            <div class="dashboard-header">
                <div id="calendar-container">
                    <button id="prev-day-btn" class="icon-btn" aria-label="Poprzedni dzień"><i data-feather="chevron-left"></i></button>
                    <h2 id="current-date"></h2>
                    <button id="next-day-btn" class="icon-btn" aria-label="Następny dzień"><i data-feather="chevron-right"></i></button>
                </div>
            </div>
            <div id="goal-eta-container"></div>
            <div class="macros-and-calories-container"></div>
            <div class="water-tracker-card"></div>
            <div id="meals-container"></div>
            <div id="workout-container"></div>
            `,
        aiChefView: () => {
            const requestsLeft = 3 - (state.currentUser.diet_plan_requests || 0);
            const canRequest = requestsLeft > 0;
            return `
                <h2>AI Chef</h2>
                <p>Twój osobisty szef kuchni, gotowy wygenerować pyszne i zdrowe plany posiłków na podstawie Twoich preferencji.</p>
                <div id="ai-chef-controls" class="btn-group">
                    <button id="generate-diet-plan-btn" class="primary-btn" ${!canRequest ? 'disabled' : ''}>
                        <i data-feather="refresh-cw"></i>
                        <span>Wygeneruj Plan Dnia (${requestsLeft}/3)</span>
                    </button>
                </div>
                <div id="diet-plan-container">
                    ${!canRequest && !state.currentUser.last_diet_plan ? '<p class="empty-list">Wykorzystano dzienny limit generowania planów. Wróć jutro!</p>' : '<p class="empty-list">Kliknij przygisk, aby wygenerować swój plan na dziś.</p>'}
                </div>`;
        },
        chatView: `
            <div class="chat-view-container">
                <div class="chat-sidebar">
                    <div class="sidebar-header">
                        <h4>Rozmowy</h4>
                        <button id="new-chat-btn" class="icon-btn" aria-label="Nowy czat"><i data-feather="plus-square"></i></button>
                    </div>
                    <div id="conversations-list" class="sidebar-content">
                        </div>
                </div>
                <div class="chat-main">
                    <div class="chat-header">
                        <h2 id="chat-title">AI Trener</h2>
                        <div id="chat-actions"></div>
                    </div>
                    <div class="chat-container">
                        <div class="chat-messages">
                            </div>
                        <form class="chat-input-container" id="chat-form">
                            <input type="text" id="chat-input" placeholder="Napisz wiadomość..." autocomplete="off">
                            <button id="chat-send-btn" class="icon-btn" type="submit"><i data-feather="send"></i></button>
                        </form>
                    </div>
                </div>
            </div>
        `,
        chatMessage: (message) => `
            <div class="chat-message ${message.role === 'user' ? 'user' : 'ai'}">
                <div class="message-bubble">
                    ${(message.content || '').replace(/\n/g, '<br>')}
                </div>
            </div>
        `,
        conversationListItem: (convo) => `
            <div class="conversation-item ${state.chat.activeConversationId === convo.id ? 'active' : ''}" data-id="${convo.id}">
                <div class="convo-info">
                    <span class="convo-title">${convo.is_pinned ? '<i data-feather="star" class="pinned-icon filled"></i>' : ''} ${convo.title}</span>
                    <span class="convo-date">${new Date(convo.created_at).toLocaleDateString('pl-PL')}</span>
                </div>
                <div class="convo-actions">
                    <button class="icon-btn pin-convo-btn" aria-label="Przypnij rozmowę"><i data-feather="star"></i></button>
                    <button class="icon-btn delete-convo-btn" aria-label="Usuń rozmowę"><i data-feather="trash-2"></i></button>
                </div>
            </div>
        `,
        manualInput: `
             <div id="analysis-error-container" class="error-message" style="margin-bottom: 1rem; display: none;"></div>
             <div class="manual-input-container">
                <input type="text" id="manual-text-input" placeholder="np. 2 jajka sadzone i 3 plastry boczku">
                <button id="manual-analyze-btn" class="primary-btn">Analizuj</button>
             </div>
             <div id="analysis-results-container"></div>`,

        socialView: `
            <div class="social-header">
                <h2>Społeczność</h2>
            </div>
            <div id="social-content">
                <div class="card" id="my-challenges-container">
                    <h4><i data-feather="target"></i> Moje Aktywne Wyzwania</h4>
                    <div id="my-challenges-list">
                        <p class="empty-list-small">Nie bierzesz udziału w żadnych wyzwaniach.</p>
                    </div>
                </div>
                <div class="card">
                    <h4><i data-feather="award"></i> Dostępne Wyzwania</h4>
                    <div id="challenges-list">
                        <p class="empty-list-small">Ładowanie wyzwań...</p>
                    </div>
                </div>
                <div class="card">
                    <h4><i data-feather="search"></i> Znajdź znajomych</h4>
                    <div class="search-container">
                        <input type="text" id="user-search-input" placeholder="Wpisz e-mail użytkownika (min. 3 znaki)...">
                        <div id="user-search-results"></div>
                    </div>
                </div>
                <div class="card">
                    <h4><i data-feather="user-plus"></i> Zaproszenia do znajomych</h4>
                    <div id="friend-requests-list">
                        <p class="empty-list-small">Brak nowych zaproszeń.</p>
                    </div>
                </div>
                <div class="card">
                    <h4><i data-feather="users"></i> Moi znajomi</h4>
                    <div id="friends-list">
                        <p class="empty-list-small">Nie masz jeszcze żadnych znajomych.</p>
                    </div>
                </div>
            </div>
        `,
        challengeItem: (challenge) => `
            <div class="challenge-item">
                <div class="challenge-info">
                    <strong>${challenge.title}</strong>
                    <p>${challenge.description}</p>
                </div>
                <button class="primary-btn join-challenge-btn" data-id="${challenge.id}">Dołącz</button>
            </div>
        `,
        // DODAJ NOWY SZABLON PONIŻEJ
        myChallengeItem: (challenge) => `
            <div class="my-challenge-item">
                <div class="my-challenge-info">
                    <strong>${challenge.challenge_info.title}</strong>
                    <span>Do: ${new Date(challenge.end_date).toLocaleDateString('pl-PL')}</span>
                </div>
                <div class="challenge-status ${challenge.status}">${challenge.status}</div>
            </div>
        `,
        userSearchResultItem: (user) => {
            let buttonHtml = '';
            switch (user.friendship_status) {
                case 'pending':
                    buttonHtml = `<button class="secondary-btn" disabled>Wysłano</button>`;
                    break;
                case 'accepted':
                    buttonHtml = `<button class="secondary-btn" disabled>Znajomi</button>`;
                    break;
                default:
                    buttonHtml = `<button class="primary-btn add-friend-btn" data-id="${user.id}"><i data-feather="user-plus"></i> Dodaj</button>`;
            }
            return `
                <div class="social-item">
                    <span>${user.name}</span>
                    <div class="social-actions">${buttonHtml}</div>
                </div>
            `;
        },
        friendRequestItem: (request) => `
            <div class="social-item" data-id="${request.id}">
                <span>${request.user_info.name}</span>
                <div class="social-actions">
                    <button class="success-btn respond-request-btn" data-status="accepted"><i data-feather="check"></i></button>
                    <button class="danger-btn respond-request-btn" data-status="declined"><i data-feather="x"></i></button>
                </div>
            </div>
        `,
        // ZASTĄP STARY SZABLON `friendItem`
        friendItem: (friend) => `
            <div class="social-item" data-id="${friend.id}">
                <div class="social-item-info">
                    <span>${friend.name}</span>
                    <div class="badges-container">
                        ${friend.completed_challenges.map(badge => `
                            <div class="challenge-badge" title="Ukończono: ${new Date(badge.end_date).toLocaleDateString('pl-PL')}">
                                <i data-feather="award"></i>
                                <span>${badge.title}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="social-actions">
                    <button class="danger-btn remove-friend-btn"><i data-feather="user-minus"></i></button>
                </div>
            </div>
        `,
        settingsProfile: (user) => `
            <form id="profile-form" class="form-grid">
                <div class="form-group"><label for="profile-name">Imię</label><input type="text" id="profile-name" value="${user.name || ''}"></div>
                <div class="form-group"><label for="profile-dob">Data urodzenia</label><input type="date" id="profile-dob" value="${user.date_of_birth || ''}"></div>
                <div class="form-group"><label for="profile-gender">Płeć</label><select id="profile-gender">
                    ${Object.values(state.enums.Gender).map(v => `<option value="${v}" ${user.gender === v ? 'selected' : ''}>${v}</option>`).join('')}
                </select></div>
                <div class="form-group"><label for="profile-height">Wzrost (cm)</label><input type="number" id="profile-height" value="${user.height || ''}"></div>
                <div class="form-group"><label for="profile-weight">Aktualna waga (kg)</label><input type="number" step="0.1" id="profile-weight" value="${user.weight || ''}"></div>
            </form>`,
        settingsGoals: (user) => {
            const macros = { p: user.protein_goal_perc || 25, f: user.fat_goal_perc || 30, c: user.carb_goal_perc || 45 };
            return `
             <form id="goals-form">
                <div class="form-group"><label for="profile-target-weight">Waga docelowa (kg)</label><input type="number" step="0.1" id="profile-target-weight" value="${user.target_weight || ''}"></div>
                <div class="form-group"><label for="profile-diet">Styl diety</label><select id="profile-diet">
                    ${Object.values(state.enums.DietStyle).map(v => `<option value="${v}" ${user.diet_style === v ? 'selected' : ''}>${v}</option>`).join('')}
                </select></div>
                <div class="form-group">
                    <label for="profile-activity">Poziom aktywności</label>
                    <select id="profile-activity">${Object.values(state.enums.ActivityLevel).map(v => `<option value="${v}" ${user.activity_level === v ? 'selected' : ''}>${v}</option>`).join('')}</select>
                </div>
                <div class="form-group form-switch">
                    <label for="add-workout-calories-toggle">Wliczaj treningi w bilans</label>
                    <label class="toggle-switch">
                        <input type="checkbox" id="add-workout-calories-toggle" ${user.add_workout_calories_to_goal ? 'checked' : ''}>
                        <span class="slider round"></span>
                    </label>
                </div>
                <p class="form-hint">Gdy włączone, kalorie spalone podczas treningu są dodawane do Twojego dziennego celu kalorycznego.</p>
                    <div class="form-group slider-container full-width">
                        <label for="weekly-goal-slider">Tygodniowy cel zmiany wagi</label>
                        <input type="range" id="weekly-goal-slider" min="-1" max="1" value="${user.weekly_goal_kg || 0}" step="0.1">
                        <output for="weekly-goal-slider">${(user.weekly_goal_kg || 0).toFixed(1)} kg</output>
                        <p id="goal-eta-display" class="form-hint" style="text-align: center; margin-top: 0.5rem; font-weight: 500; min-height: 1.2em;"></p>
                    </div>
                <button type="button" id="suggest-ai-goals-btn" class="secondary-btn full-width"><i data-feather="cpu"></i> Sugeruj cele z AI</button>
                <div class="form-group full-width">
                    <label for="profile-calories">Cel kaloryczny (kcal)</label>
                    <input type="number" id="profile-calories" value="${user.calorie_goal || 2000}">
                </div>
                <div class="form-group full-width">
                    <label>Rozkład makroskładników (%)</label>
                    <div class="macro-sliders">
                        <div class="slider-group">
                            <span>B</span>
                            <input type="range" class="macro-slider" data-macro="p" min="0" max="100" value="${macros.p}">
                            <output>${macros.p}%</output>
                        </div>
                        <div class="slider-group">
                            <span>T</span>
                            <input type="range" class="macro-slider" data-macro="f" min="0" max="100" value="${macros.f}">
                            <output>${macros.f}%</output>
                        </div>
                         <div class="slider-group">
                            <span>W</span>
                            <input type="range" class="macro-slider" data-macro="c" min="0" max="100" value="${macros.c}">
                            <output>${macros.c}%</output>
                        </div>
                    </div>
                </div>
                <div class="form-grid goals-grid">
                    <div class="form-group"><label>Białko (g)</label><input type="number" id="profile-protein-g" disabled value="${user.protein_goal || 0}"></div>
                    <div class="form-group"><label>Tłuszcz (g)</label><input type="number" id="profile-fat-g" disabled value="${user.fat_goal || 0}"></div>
                    <div class="form-group"><label>Węgle (g)</label><input type="number" id="profile-carbs-g" disabled value="${user.carbs_goal || 0}"></div>
                </div>
             </form>`
        },
        settingsTastes: (prefs) => `
            <div id="tastes-container">
                <p>Przeciągnij, aby zmienić kolejność. Twoje ulubione produkty (na górze listy) będą miały priorytet w sugestiach AI Chefa.</p>
                ${Object.keys(prefs).map(key => `
                    <div class="taste-category">
                        <h4>${{proteins:'Białka', carbs:'Węglowodany', fats:'Tłuszcze'}[key]}</h4>
                        <ul class="sortable-list" id="taste-${key}" data-category="${key}">
                            ${(prefs[key] || []).map(item => `<li><i data-feather="menu" class="drag-handle"></i><span>${item}</span><button class="delete-pref-item icon-btn"><i data-feather="x"></i></button></li>`).join('')}
                        </ul>
                        <form class="add-pref-form" data-category="${key}">
                            <input type="text" placeholder="Dodaj nowy produkt...">
                            <button type="submit" class="icon-btn"><i data-feather="plus"></i></button>
                        </form>
                    </div>
                `).join('')}
            </div>`,
        settingsApp: (user) => `
            <div id="app-settings-container">
                <h4>Motyw</h4>
                <div class="theme-switcher">
                    <button class="theme-btn" data-theme="light"><i data-feather="sun"></i> Jasny</button>
                    <button class="theme-btn" data-theme="dark"><i data-feather="moon"></i> Ciemny</button>
                    <button class="theme-btn" data-theme="system"><i data-feather="monitor"></i> Systemowy</button>
                </div>

                <h4>Funkcje Społecznościowe</h4>
                <div class="form-group form-switch">
                    <label for="social-profile-toggle">Aktywuj profil społecznościowy</label>
                    <label class="toggle-switch">
                        <input type="checkbox" id="social-profile-toggle" ${user.is_social_profile_active ? 'checked' : ''}>
                        <span class="slider round"></span>
                    </label>
                </div>
                <p class="form-hint">Pozwól innym użytkownikom Cię znaleźć i zapraszać do znajomych.</p>

                <h4>Informacje Prawne</h4>
                <div class="legal-links">
                    <a href="/regulamin.html" target="_blank" class="legal-link">Regulamin</a>
                    <a href="/polityka-prywatnosci.html" target="_blank" class="legal-link">Polityka Prywatności</a>
                    <a href="/zastrzezenie.html" target="_blank" class="legal-link">Zastrzeżenie (Disclaimer)</a>
                </div>

                <h4 class="danger-zone-title">Strefa Niebezpieczeństwa</h4>
                <div class="danger-zone">
                    <button id="logout-btn" class="secondary-btn"><i data-feather="log-out"></i>Wyloguj</button>
                    <button id="delete-account-btn" class="danger-btn"><i data-feather="trash-2"></i>Usuń konto</button>
                </div>
            </div>
            `,
        // ZAKTUALIZOWANY SZABLON
        interactiveIngredientList: (ingredients, isEditable = true) => {
            if (!ingredients || ingredients.length === 0) {
                return '<p class="empty-list-small">Brak zdefiniowanych składników.</p>';
            }
            return `
                <div class="interactive-ingredients">
                    ${ingredients.map((item, index) => {
                        const name = item.name || 'Nieznany składnik';
                        const weight = Math.round(item.quantity_grams || 0);
                        // Odczytujemy dane bazowe (NOWOŚĆ)
                        const baseNutrients = item.nutrients_per_100g || {calories: 0, protein: 0, fat: 0, carbs: 0};

                        return `
                            <div class="ingredient-item" 
                                 data-index="${index}"
                                 data-kcal-per-100g="${baseNutrients.calories}"
                                 data-protein-per-100g="${baseNutrients.protein}"
                                 data-fat-per-100g="${baseNutrients.fat}"
                                 data-carbs-per-100g="${baseNutrients.carbs}">

                                <input type="checkbox" class="ingredient-checkbox" ${isEditable ? '' : 'disabled'} checked>
                                <span class="ingredient-name">${name}</span>
                                <div class="ingredient-controls">
                                    <input type="number" class="ingredient-weight-input" value="${weight}" ${isEditable ? '' : 'disabled'}>
                                    <span>g</span>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        },
    };

    // === FUNKCJE POMOCNICZE ===
    let macroChartInstance = null;
    let weightChartInstance = null;

    const setLoading = (isLoading) => { state.isLoading = isLoading; selectors.loader.classList.toggle('hidden', !isLoading); };
    const showNotification = (message, type = 'success') => {
        selectors.notificationBar.textContent = message;
        selectors.notificationBar.className = `notification ${type}`;
        selectors.notificationBar.classList.add('show');
        setTimeout(() => { selectors.notificationBar.classList.remove('show'); }, 3000);
    };
    const toISODate = (dateObj) => {
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    // Funkcja do konwersji pliku na base64
    const toBase64 = file => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });

    // NOWA FUNKCJA: Kompresja obrazu przed wysłaniem
    const compressImage = (file) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const MAX_WIDTH = 1000; // Maksymalna szerokość obrazu
                    let width = img.width;
                    let height = img.height;

                    if (width > MAX_WIDTH) {
                        height *= MAX_WIDTH / width;
                        width = MAX_WIDTH;
                    }

                    canvas.width = width;
                    canvas.height = height;

                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                    // Kompresja do JPEG z jakością 70%
                    canvas.toBlob((blob) => {
                        if (blob) {
                            resolve(blob);
                        } else {
                            reject(new Error("Błąd kompresji obrazu do Blob."));
                        }
                    }, 'image/jpeg', 0.7);
                };
                img.onerror = (error) => reject(error);
                img.src = event.target.result;
            };
            reader.onerror = (error) => reject(error);
            reader.readAsDataURL(file);
        });
    };

    const featherReplace = () => { try { feather.replace({ width: '1em', height: '1em' }) } catch (e) {} };
    const debounce = (func, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };
    const formatDate = (date) => {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };
    const getCssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    // === GŁÓWNA LOGIKA RENDEROWANIA APLIKACJI (bez zmian) ===
    const render = {
        app: () => {
            if (state.token && state.currentUser) {
                selectors.appContainer.classList.remove('hidden');
                selectors.authContainer.innerHTML = '';
                selectors.authContainer.classList.add('hidden');
                $('.view[data-view-name="dashboard"]').innerHTML = templates.dashboardView;
                $('.view[data-view-name="aiChef"]').innerHTML = templates.aiChefView();
                $('.view[data-view-name="social"]').innerHTML = templates.socialView;
                $('.view[data-view-name="chat"]').innerHTML = templates.chatView;
                render.view(state.activeView);
            } else {
                selectors.appContainer.classList.add('hidden');
                selectors.authContainer.innerHTML = templates.authBox;
                selectors.authContainer.classList.remove('hidden');

                // Dynamiczne wstawienie linku Google OAuth z poprawnymi parametrami
                const googleLoginPlaceholder = $('#google-login-placeholder');
                if (googleLoginPlaceholder) {
                    const clientId = '877107890429-q1kiihn9vd95h1alg40p700hdbqvj5dq.apps.googleusercontent.com';
                    const redirectUri = 'https://aikcallapp.click/api/auth/callback/google';
                    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=email%20profile&access_type=offline`;

                    googleLoginPlaceholder.innerHTML = `
                        <a href="${googleAuthUrl}" class="secondary-btn google-btn">
                            <svg aria-hidden="true" width="20" height="20" viewBox="0 0 20 20"><path d="M19.87.5h-19.74c-.07 0-.13.06-.13.13v19.74c0 .07.06.13.13.13h19.74c.07 0 .13-.06.13-.13V.63c0-.07-.06-.13-.13-.13Z" fill="#fff"></path><path d="M10.18 14.59c-2.37 0-4.47-1.92-4.47-4.28s1.9-4.28 4.47-4.28c1.25 0 2.24.49 3.08 1.3l-1.35 1.3c-.39-.37-.99-.75-1.73-.75-1.47 0-2.68 1.24-2.68 2.75s1.2 2.75 2.68 2.75c1.73 0 2.37-1.25 2.47-1.88h-2.47v-1.63h4.13c.04.25.06.49.06.75 0 2.84-1.92 4.88-4.19 4.88Z" fill="#4285F4"></path></svg>
                            <span>Zaloguj się z Google</span>
                        </a>
                    `;
                }
                addAuthEventListeners();
            }
        },
        view: (viewName) => {
            state.activeView = viewName;
            $$('.view').forEach(v => v.classList.toggle('active', v.dataset.viewName === viewName));
            $$('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.view === viewName));

            if (viewName === 'dashboard') render.dashboard();
            else if (viewName === 'aiChef') {
                if (state.currentUser.last_diet_plan) {
                    try {
                        // Plan jest już w formacie JSON stringa, więc wystarczy go sparsować
                        const plan = JSON.parse(state.currentUser.last_diet_plan);
                        render.dietPlan(plan);
                    } catch(e) {
                         console.error("Błąd parsowania planu diety z profilu użytkownika:", e);
                         // Jeśli błąd parsowania, wyświetl pusty plan
                         render.dietPlan([]);
                    }
                } else {
                    // Jeśli brak planu, wyświetl domyślny komunikat z template'u
                    $('#diet-plan-container').innerHTML = '<p class="empty-list">Kliknij przygisk, aby wygenerować swój plan na dziś.</p>';
                }
            }
            else if (viewName === 'social') render.social();
            else if (viewName === 'analysis') render.analysisPage();
            else if (viewName === 'chat') render.chat();

            $('#header-title').textContent = (state.currentUser && state.currentUser.name) ? `Witaj, ${state.currentUser.name}` : 'AIKcal';
            featherReplace();
        },
        dashboard: async () => {
            try {
                const summary = await api.getSummaryByDate(toISODate(state.currentDate));
                state.summary = summary;

                $('.macros-and-calories-container').innerHTML = render.macrosAndCalories(summary);
                $('.water-tracker-card').innerHTML = render.waterTracker(summary);
                $('#meals-container').innerHTML = render.meals(summary);
                $('#workout-container').innerHTML = render.workouts(summary);
                $('#current-date').textContent = state.currentDate.toLocaleDateString('pl-PL', { weekday: 'long', day: 'numeric', month: 'long' });
                $('#goal-eta-container').innerHTML = summary.goal_achievement_date ? `<div class="eta-chip"><i data-feather="flag"></i>Szacowane osiągnięcie celu: ${summary.goal_achievement_date}</div>` : '';
                featherReplace();
            } catch (error) { console.error("Błąd ładowania dashboardu:", error); }
        },
        macrosAndCalories: (s) => {
            return `
                ${render.progressRing(s.calories_consumed, s.calorie_goal, 'Kcal', 'var(--primary-color)', 'var(--primary-color-dark)', 100)}
                ${render.progressRing(s.protein_consumed, s.protein_goal, 'Białko', 'var(--protein-color)', 'var(--protein-color-dark)', 75)}
                ${render.progressRing(s.fat_consumed, s.fat_goal, 'Tłuszcz', 'var(--fat-color)', 'var(--fat-color-dark)', 75)}
                ${render.progressRing(s.carbs_consumed, s.carb_goal, 'Węgle', 'var(--carbs-color)', 'var(--carbs-color-dark)', 75)}
            `;
        },
        waterTracker: (s) => `
            <div class="water-info">
                <h3><i data-feather="droplet"></i> Woda</h3>
                <div class="water-value">${s.water_consumed} / ${s.water_goal} ml</div>
            </div>
            <div class="water-controls">
                <button class="water-btn" data-amount="-250" aria-label="Odejmij wodę" ${s.water_consumed <= 0 ? 'disabled' : ''}><i data-feather="minus"></i></button>
                <button class="water-btn" data-amount="250" aria-label="Dodaj wodę"><i data-feather="plus"></i></button>
            </div>`,
        progressRing: (consumed, goal, label, color, overColor, size) => {
            const r = size / 2 - (size > 80 ? 6 : 5);
            const circ = 2 * Math.PI * r;
            const progress = goal > 0 ? Math.min(consumed / goal, 1) : 0;
            const overProgress = goal > 0 ? Math.max(0, (consumed / goal) - 1) : 0;
            const offset = circ - progress * circ;
            const overOffset = circ - overProgress * circ;
            const isCalories = label === 'Kcal';
            return `
                <div class="macro-card" style="width:${size}px; height:${size}px;">
                    <div class="progress-ring-container">
                        <svg class="progress-ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                            <circle class="progress-ring__bg" r="${r}" cx="${size/2}" cy="${size/2}" style="stroke-width: ${isCalories ? 10 : 7}px;"/>
                            <circle class="progress-ring__ring" r="${r}" cx="${size/2}" cy="${size/2}" style="stroke-dasharray:${circ}; stroke-dashoffset:${offset}; stroke:${color}; stroke-width: ${isCalories ? 10 : 7}px;"/>
                            <circle class="progress-ring__over" r="${r}" cx="${size/2}" cy="${size/2}" style="stroke-dasharray:${circ}; stroke-dashoffset:${overOffset}; stroke: ${overColor}; stroke-width: ${isCalories ? 10 : 7}px;"/>
                        </svg>
                        <div class="progress-ring__text">
                            <span class="progress-ring__value" style="font-size: ${isCalories ? '1.2rem' : '0.9rem'};">${Math.round(consumed)}</span>
                            <span class="progress-ring__goal" style="font-size: ${isCalories ? '0.8rem' : '0.6rem'};">${isCalories ? `/ ${goal} ${label.toLowerCase()}` : `/ ${goal}g`}</span>
                        </div>
                    </div>
                    ${isCalories ? '' : `<p class="macro-label">${label}</p>`}
                </div>`;
        },
        meals: (s) => {
            const categories = state.enums.MealCategory;
            return categories.map(cat => {
                const categoryId = cat.replace(/\s+/g, '-');
                const mealsInCategory = s.meals.filter(m => m.category === cat);

                return `
                <div class="meal-category-group">
                    <div class="meal-category-header collapsible" data-target-list="#meals-list-${categoryId}">
                        <span>${cat}</span>
                        <div class="header-right">
                            <div class="add-meal-action-group">
                                <button class="icon-btn add-meal-btn" data-category="${cat}" data-type="image" aria-label="Dodaj zdjęcie"><i data-feather="camera"></i></button>
                                <button class="icon-btn add-meal-btn" data-category="${cat}" data-type="voice" aria-label="Dodaj głosem"><i data-feather="mic"></i></button>
                                <button class="icon-btn add-meal-btn" data-category="${cat}" data-type="manual" aria-label="Dodaj ręcznie"><i data-feather="edit-3"></i></button>
                            </div>
                            <i data-feather="chevron-down" class="collapse-icon"></i>
                        </div>
                    </div>
                    <div class="meals-list" id="meals-list-${categoryId}">
                        ${mealsInCategory.length > 0 ? mealsInCategory.flatMap(m => m.entries).map(entry => `
                            <div class="meal-item" data-id="${entry.id}" data-meal-id="${entry.meal_id}">
                                <div class="meal-item-header meal-item-toggle">
                                    <div class="meal-info">
                                        <span>${entry.product_name}</span>
                                        <span class="meal-macros">${Math.round(entry.calories)} kcal &middot; B:${Math.round(entry.protein)} T:${Math.round(entry.fat)} W:${Math.round(entry.carbs)}</span>
                                    </div>
                                    <div class="header-icons">
                                        <button class="icon-btn edit-meal-entry-btn" data-entry='${JSON.stringify(entry)}'><i data-feather="edit"></i></button>
                                        <button class="icon-btn delete-meal-entry-btn" data-id="${entry.id}"><i data-feather="trash-2"></i></button>
                                        <i data-feather="chevron-down" class="collapse-icon"></i>
                                    </div>
                                </div>
                                <div class="meal-item-ingredients">
                                    ${templates.interactiveIngredientList(entry.deconstruction_details, false)}
                                </div>
                            </div>
                        `).join('') : '<p class="empty-list-small">Brak posiłków</p>'}
                    </div>
                </div>
            `}).join('');
        },
        workouts: (s) => {
            return `
            <div class="meal-category-group">
                <div class="meal-category-header collapsible" data-target-list="#workouts-list">
                    <span>Trening</span>
                    <div class="header-right">
                        <span class="training-summary">Spalono dziś: ${s.total_calories_burned_today || 0} kcal</span>
                        <div class="add-meal-action-group">
                            <button class="icon-btn add-workout-btn" data-type="voice" aria-label="Dodaj głosem"><i data-feather="mic"></i></button>
                            <button class="icon-btn add-workout-btn" data-type="manual" aria-label="Dodaj ręcznie"><i data-feather="edit-3"></i></button>
                        </div>
                        <i data-feather="chevron-down" class="collapse-icon"></i>
                    </div>
                </div>
                <div class="meals-list" id="workouts-list">
                    ${s.workouts.map(w => `
                        <div class="meal-item" data-id="${w.id}">
                            <div class="meal-info">
                                <span>${w.name}</span>
                                <span class="meal-macros">${w.calories_burned > 0 ? `Spalono: ${w.calories_burned} kcal` : ''}</span>
                            </div>
                            <div class="meal-actions">
                                <button class="icon-btn delete-workout-btn" data-id="${w.id}"><i data-feather="trash-2"></i></button>
                            </div>
                        </div>
                    `).join('') || '<p class="empty-list-small">Brak treningów</p>'}
                </div>
            </div>
            `;
        },
        modal: (title, content, showFooter = true, modalElement = selectors.addMealModal) => {
            modalElement.querySelector('h3').textContent = title;
            const modalBodyElement = modalElement.querySelector('#modal-body') || modalElement.querySelector('#settings-body') || modalElement.querySelector('#details-modal-body') || modalElement.querySelector('#edit-meal-entry-modal-body'); // NOWE: Dodano selektor dla edycji
            if (modalBodyElement) {
                modalBodyElement.innerHTML = content;
            }
            modalElement.querySelector('.modal-footer').classList.toggle('hidden', !showFooter);
            modalElement.classList.remove('hidden');
            featherReplace();
        },
        analysisResults: (result, category) => {
            const container = $('#analysis-results-container');
            if (!container) return;

            if (!result || !result.aggregated_meal || !result.aggregated_meal.name) {
                container.innerHTML = `<p class="error-message">Nie udało się przeanalizować produktu.</p>`;
                selectors.addMealModal.querySelector('.modal-footer').classList.add('hidden');
                return;
            }

            const meal = result.aggregated_meal;
            const ingredients = result.deconstruction_details;

            pristineRecipeData = ingredients;

            // ### START OF REPLACEMENT 1 ###
            container.innerHTML = `
                <div class="analysis-summary">
                    <div class="summary-header">
                        <span id="analysis-final-name">${meal.name}</span>
                        <div class="total-weight-editor">(<input type="number" id="analysis-total-weight-input" value="${Math.round(meal.quantity_grams)}">g)</div>
                    </div>
                    <div class="summary-macros" id="analysis-macros-summary">${Math.round(meal.calories)} kcal &middot; B:${Math.round(meal.protein)} T:${Math.round(meal.fat)} W:${Math.round(meal.carbs)}</div>
                </div>
                <div class="ingredients-toggle">
                    <span>Składniki</span>
                    <i data-feather="chevron-down" class="collapse-icon"></i>
                </div>
                <div class="meal-item-ingredients">
                    ${templates.interactiveIngredientList(ingredients, true)}
                </div>
                <input type="hidden" id="analysis-original-data" value='${JSON.stringify(result)}'>
            `;
            // ### END OF REPLACEMENT 1 ###

            selectors.addMealModal.querySelector('.modal-footer').classList.remove('hidden');
            
            const newContainer = container.cloneNode(true);
            container.parentNode.replaceChild(newContainer, container);

            newContainer.addEventListener('input', (e) => {
                if (e.target.classList.contains('total-weight-input') || e.target.classList.contains('ingredient-weight-input') || e.target.classList.contains('ingredient-checkbox')) {
                    handle.recalculateMacros('analysis-original-data', e.target);
                }
            });

            // Listener for the new ingredients toggle
            newContainer.querySelector('.ingredients-toggle')?.addEventListener('click', (e) => {
                const toggle = e.currentTarget;
                const ingredientsList = toggle.nextElementSibling;
                toggle.classList.toggle('open');
                ingredientsList.classList.toggle('open');
            });


            featherReplace();
        },
        calendar: () => {
            const today = new Date();
            const year = state.currentDate.getFullYear();
            const month = state.currentDate.getMonth();
            const monthName = state.currentDate.toLocaleDateString('pl-PL', { month: 'long', year: 'numeric' });
            let gridHtml = `<div class="calendar-header">
                <button id="calendar-prev-month" class="icon-btn"><i data-feather="chevron-left"></i></button>
                <h3>${monthName}</h3>
                <button id="calendar-next-month" class="icon-btn"><i data-feather="chevron-right"></i></button>
            </div><div class="calendar-grid">`;
            const daysOfWeek = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd'];
            daysOfWeek.forEach(day => { gridHtml += `<div class="calendar-day-name">${day}</div>`; });
            const firstDay = (new Date(year, month, 1).getDay() + 6) % 7;
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            for (let i = 0; i < firstDay; i++) { gridHtml += `<div></div>`; }
            for (let day = 1; day <= daysInMonth; day++) {
                const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
                const isSelected = day === state.currentDate.getDate();
                let dayClass = 'calendar-day';
                if(isToday) dayClass += ' today';
                if(isSelected) dayClass += ' selected';
                gridHtml += `<div class="${dayClass}" data-day="${day}">${day}</div>`;
            }
            gridHtml += `</div>`;
            return gridHtml;
        },
        dietPlan: (plan) => {
            const container = $('#diet-plan-container');
            if (!container) return;
            if (!plan || plan.length === 0) {
                 container.innerHTML = '<p class="empty-list">AI Chef nie mógł wygenerować planu. Spróbuj ponownie.</p>';
            } else {
                container.innerHTML = plan.map(meal => `
                    <div class="diet-plan-card">
                        <h3>${meal.category}: ${meal.meal_name}</h3>
                        <div class="diet-plan-content">
                            <h4>Składniki:</h4>
                            <div class="meal-items-wrapper">
                                ${meal.products.map(p => `
                                    <div class="meal-item">
                                        <div class="meal-info">
                                            <span>${p.name} (${p.display_quantity_text || `${p.quantity_grams}g`})</span>
                                            <span class="meal-macros">${Math.round(p.calories)} kcal &middot; B:${Math.round(p.protein)} T:${Math.round(p.fat)} W:${Math.round(p.carbs)}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <h4>Przygotowanie:</h4>
                            <p class="recipe-steps">${(meal.recipe || '').replace(/\\n/g, '<br>')}</p>
                        </div>
                    </div>
                `).join('');
            }
            featherReplace();
        },
        analysisPage: async () => {
            if (!state.analysisRange.startDate || !state.analysisRange.endDate) {
                handle.setAnalysisDateRange(7);
            } else {
                selectors.analysisStartDate.value = toISODate(state.analysisRange.startDate);
                selectors.analysisEndDate.value = toISODate(state.analysisRange.endDate);
            }

            try {
                const dataForCharts = await api.getAnalysisData(
                    toISODate(state.analysisRange.startDate),
                    toISODate(state.analysisRange.endDate)
                );
                state.analysisRange.data = dataForCharts;
                render.renderAnalysisContent(dataForCharts, state.analysis.aiSummary);
            } catch (error) {
                console.error("Błąd ładowania danych dla wykresów analizy:", error);
                showNotification("Nie udało się załadować danych dla wykresów.", "error");
                state.analysisRange.data = null;
            }

            try {
                const latestAiAnalysis = await api.getLatestAnalysis();
                state.analysis.aiSummary = latestAiAnalysis.ai_coach_summary;
                state.analysis.startDate = new Date(latestAiAnalysis.analysis_start_date);
                state.analysis.endDate = new Date(latestAiAnalysis.analysis_end_date);
                state.analysis.generatedAt = state.currentUser.last_analysis_generated_at ? new Date(state.currentUser.last_analysis_generated_at) : null;

                selectors.aiCoachContainer.classList.remove('hidden');
                selectors.aiCoachSummary.innerHTML = (state.analysis.aiSummary || '').replace(/\n/g, '<br>');

            } catch (error) {
                console.warn("Brak dostępnej analizy AI lub jest przestarzała:", error.message);
                selectors.aiCoachContainer.classList.add('hidden');
                state.analysis.aiSummary = null;
                state.analysis.generatedAt = null;
                state.analysis.startDate = null;
                state.analysis.endDate = null;
            }

            handle.updateAnalysisButtonState();
            addAnalysisEventListeners();
        },
        renderAnalysisContent: (dataForCharts, aiSummaryText) => {
            if (dataForCharts) {
                selectors.macroChartContainer.classList.remove('hidden');
                selectors.weightChartContainer.classList.remove('hidden');
                selectors.workoutsSummaryContainer.classList.remove('hidden');

                selectors.totalWorkouts.textContent = dataForCharts.total_workouts;
                selectors.totalCaloriesBurned.textContent = dataForCharts.total_calories_burned;

                if (macroChartInstance) macroChartInstance.destroy();
                const macroCtx = document.getElementById('macro-chart').getContext('2d');
                const proteinColor = getCssVar('--protein-color');
                const fatColor = getCssVar('--fat-color');
                const carbsColor = getCssVar('--carbs-color');

                macroChartInstance = new Chart(macroCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Białko', 'Tłuszcz', 'Węglowodany'],
                        datasets: [{
                            data: [dataForCharts.avg_macros.protein, dataForCharts.avg_macros.fat, dataForCharts.avg_macros.carbs],
                            backgroundColor: [proteinColor, fatColor, carbsColor],
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: getCssVar('--text-primary') } },
                            title: { display: true, text: `Średnie dzienne spożycie (od ${formatDate(dataForCharts.analysis_start_date)} do ${formatDate(dataForCharts.analysis_end_date)})`, color: getCssVar('--text-primary') }
                        }
                    }
                });

                if (weightChartInstance) weightChartInstance.destroy();
                const weightCtx = document.getElementById('weight-chart').getContext('2d');
                weightChartInstance = new Chart(weightCtx, {
                    type: 'line',
                    data: {
                        labels: dataForCharts.weight_chart_data.labels,
                        datasets: [{
                            label: 'Waga (kg)',
                            data: dataForCharts.weight_chart_data.values,
                            borderColor: getCssVar('--primary-color'),
                            tension: 0.3,
                            pointBackgroundColor: getCssVar('--primary-color-dark'),
                            pointBorderColor: getCssVar('--primary-color-dark'),
                            pointRadius: 5, pointHoverRadius: 7, fill: false
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        scales: {
                            x: {
                                type: 'time',
                                time: { unit: 'day', tooltipFormat: 'dd.MM.yyyy', displayFormats: { day: 'dd.MM' } },
                                title: { display: true, text: 'Data', color: getCssVar('--text-secondary') },
                                ticks: { color: getCssVar('--text-secondary') },
                                grid: { color: getCssVar('--border-color') }
                            },
                            y: {
                                title: { display: true, text: 'Waga (kg)', color: getCssVar('--text-secondary') },
                                ticks: { color: getCssVar('--text-secondary') },
                                grid: { color: getCssVar('--border-color') }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${context.parsed.y} kg` } },
                            title: { display: true, text: `Zmiana wagi (od ${formatDate(dataForCharts.analysis_start_date)} do ${formatDate(dataForCharts.analysis_end_date)})`, color: getCssVar('--text-primary') }
                        }
                    }
                });
            } else {
                selectors.macroChartContainer.classList.add('hidden');
                selectors.weightChartContainer.classList.add('hidden');
                selectors.workoutsSummaryContainer.classList.add('hidden');
            }

            if (aiSummaryText) {
                selectors.aiCoachContainer.classList.remove('hidden');
                selectors.aiCoachSummary.innerHTML = (aiSummaryText || '').replace(/\n/g, '<br>');
            } else {
                selectors.aiCoachContainer.classList.add('hidden');
            }

            featherReplace();
        },
        chat: async () => {
            try {
                const conversations = await api.getConversations();
                state.chat.conversations = conversations;
                const conversationsList = $('#conversations-list');
                if (conversations.length > 0) {
                    conversationsList.innerHTML = conversations.map(templates.conversationListItem).join('');
                } else {
                    conversationsList.innerHTML = '<p class="empty-list-small">Kliknij "+", aby zacząć.</p>';
                }
                
                let activeConvo = null;
                if (state.chat.activeConversationId) {
                    activeConvo = conversations.find(c => c.id === state.chat.activeConversationId);
                }
                if (!activeConvo && conversations.length > 0) {
                    activeConvo = conversations[0];
                    state.chat.activeConversationId = activeConvo.id;
                }
                
                const messagesContainer = $('.chat-messages');
                if (activeConvo) {
                    const fullConversation = await api.getConversationMessages(activeConvo.id);
                    state.chat.messages = fullConversation.messages;
                    messagesContainer.innerHTML = state.chat.messages.map(templates.chatMessage).join('');
                    $('#chat-title').textContent = activeConvo.title;
                } else {
                    messagesContainer.innerHTML = templates.chatMessage({role: 'ai', content: 'Cześć! Jestem Twoim trenerem AI. Kliknij "+" w panelu bocznym, aby zacząć nową rozmowę.'});
                    $('#chat-title').textContent = 'AI Trener';
                }
                messagesContainer.scrollTop = messagesContainer.scrollHeight;

                addChatEventListeners();
                featherReplace();

            } catch (error) {
                console.error("Błąd ładowania widoku czatu:", error);
                showNotification("Nie udało się załadować danych czatu.", "error");
            }
        },
        social: async () => {
            if (!state.currentUser.is_social_profile_active) {
                $('#social-content').innerHTML = `
                    <div class="card text-center" style="text-align: center; padding: 2rem;">
                        <h3>Funkcje społecznościowe są wyłączone.</h3>
                        <p style="margin: 1rem 0;">Aby wyszukiwać znajomych, aktywuj profil w Ustawieniach.</p>
                        <button id="go-to-settings-btn" class="primary-btn">Przejdź do Ustawień</button>
                    </div>`;
                featherReplace();
                return;
            }
            try {
                const [friends, requests, availableChallenges, myChallenges] = await Promise.all([
                    api.getFriends(),
                    api.getFriendRequests(),
                    api.getChallenges(),
                    api.getMyChallenges()
                ]);
                state.social.challenges = myChallenges;
                const myChallengeIds = myChallenges.map(c => c.challenge_id);

                $('#my-challenges-list').innerHTML = myChallenges.length > 0
                    ? myChallenges.map(templates.myChallengeItem).join('')
                    : '<p class="empty-list-small">Nie bierzesz udziału w żadnych wyzwaniach.</p>';

                const availableChallengesContainer = $('#challenges-list');
                if (Array.isArray(availableChallenges) && availableChallenges.length > 0) {
                    availableChallengesContainer.innerHTML = availableChallenges.map(challenge => {
                        const isJoined = myChallengeIds.includes(challenge.id);
                        return `
                            <div class="challenge-item">
                                <div class="challenge-info">
                                    <strong>${challenge.title}</strong>
                                    <p>${challenge.description}</p>
                                </div>
                                <button class="primary-btn join-challenge-btn" data-id="${challenge.id}" ${isJoined ? 'disabled' : ''}>
                                    ${isJoined ? 'Dołączono' : 'Dołącz'}
                                </button>
                            </div>
                        `;
                    }).join('');
                } else {
                    availableChallengesContainer.innerHTML = '<p class="empty-list-small">Brak dostępnych wyzwań.</p>';
                }

                $('#friends-list').innerHTML = friends.length > 0 ? friends.map(templates.friendItem).join('') : '<p class="empty-list-small">Brak znajomych.</p>';
                $('#friend-requests-list').innerHTML = requests.length > 0 ? requests.map(templates.friendRequestItem).join('') : '<p class="empty-list-small">Brak nowych zaproszeń.</p>';

                addSocialEventListeners();
                featherReplace();
            } catch (error) {
                $('#social-content').innerHTML = `<p class="error-message">Nie można załadować danych.</p>`;
            }
        },
    };

    // === HANDLERY ZDARZEŃ ===
    const handle = {
        login: async (e) => {
            e.preventDefault();
            $('#auth-error').textContent = '';
            try {
                const formData = new URLSearchParams();
                formData.append('username', $('#login-email').value);
                formData.append('password', $('#login-password').value);

                const tokenData = await api.request('/users/login', { // Zmieniono endpoint
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });

                state.token = tokenData.access_token;
                localStorage.setItem('token', state.token);
                await initApp(true);
            } catch (error) {
                $('#auth-error').textContent = 'Nieprawidłowy email lub hasło.';
            }
        },
        register: async (e) => {
            e.preventDefault();
            try {
                await api.register($('#register-email').value, $('#register-password').value);
                showNotification('Rejestracja pomyślna! Możesz się teraz zalogować.', 'success');
                handle.showLoginForm();
                $('#login-email').value = $('#register-email').value;
                $('#register-form').reset();
            } catch (error) { $('#auth-error').textContent = error.message; }
        },
        logout: () => {
            state.token = null;
            state.currentUser = null;
            localStorage.removeItem('token');
            showNotification('Wylogowano pomyślnie.', 'success');
            render.app();
        },
        deleteAccount: async () => {
            const confirmDelete = await new Promise(resolve => {
                const modalHtml = `
                    <div id="confirm-modal" class="modal-overlay">
                        <div class="modal-content small">
                            <h3>Potwierdź usunięcie</h3>
                            <p>CZY NA PEWNO CHCESZ TRWALE USUNĄĆ SWOJE KONTO? Ta operacja jest nieodwracalna.</p>
                            <div class="modal-footer" style="justify-content: space-around;">
                                <button id="cancel-delete-btn" class="secondary-btn">Anuluj</button>
                                <button id="confirm-delete-btn" class="danger-btn">Usuń konto</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                const confirmModal = $('#confirm-modal');
                $('#confirm-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(true); });
                $('#cancel-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(false); });
                confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) { confirmModal.remove(); resolve(false); } });
            });

            if (confirmDelete) {
                try { await api.deleteMe(); handle.logout(); }
                catch (error) { showNotification('Nie udało się usunąć konta.', 'error'); }
            }
        },
        showRegisterForm: (e) => { e.preventDefault(); $('#login-form').classList.add('hidden'); $('#register-form').classList.remove('hidden'); $('#auth-error').textContent = ''; $('#auth-title').textContent = 'Zarejestruj się'; $('#auth-switch').innerHTML = 'Masz już konto? <a href="#" id="show-login">Zaloguj się</a>'; },
        showLoginForm: (e) => { e?.preventDefault(); $('#register-form').classList.add('hidden'); $('#forgot-password-form').classList.add('hidden'); $('#login-form').classList.remove('hidden'); $('#auth-error').textContent = ''; $('#auth-title').textContent = 'Zaloguj się'; $('#auth-switch').innerHTML = 'Nie masz konta? <a href="#" id="show-register">Zarejestruj się</a>'; },
        // --- NOWE FUNKCJE ---
        showForgotPasswordForm: (e) => {
            e.preventDefault();
            $('#login-form').classList.add('hidden');
            $('#register-form').classList.add('hidden');
            $('#forgot-password-form').classList.remove('hidden');
            $('#auth-error').textContent = '';
            $('#auth-title').textContent = 'Odzyskaj hasło';
            $('#auth-switch').innerHTML = 'Wróć do <a href="#" id="show-login">logowania</a>';
        },
        forgotPassword: async (e) => {
            e.preventDefault();
            const email = $('#forgot-email').value;
            try {
                await api.requestPasswordReset(email);
                showNotification('Jeśli konto istnieje, link do resetu hasła został wysłany.', 'success');
                handle.showLoginForm();
            } catch (error) { /* Błąd obsłużony globalnie */ }
        },
        changeDate: (offset) => { state.currentDate.setDate(state.currentDate.getDate() + offset); render.dashboard(); },
        openAddMealModal: (category) => {
            // DODAJ TĘ LINIĘ, ABY ZAPISAĆ KATEGORIĘ W OKNIE
            selectors.addMealModal.dataset.currentCategory = category;

            render.modal(`Dodaj do: ${category}`, templates.manualInput, false);
            addManualInputListeners(category);
        },
        openSettingsModal: () => {
            render.modal('Ustawienia', templates.settingsProfile(state.currentUser), true, selectors.settingsModal); // Przekazano modalElement
            addSettingsEventListeners();
            handle.switchSettingsTab('tab-profile');
        },
        openCalendarModal: () => {
            selectors.calendarModal.querySelector('#calendar-modal-body').innerHTML = render.calendar();
            selectors.calendarModal.classList.remove('hidden');
            featherReplace();
            addCalendarModalEventListeners();
        },
        closeModal: (modal) => modal.classList.add('hidden'),
        themeChange: (theme, save = true) => {
            const isDark = (theme === 'dark') || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
            document.documentElement.className = isDark ? 'dark' : '';
            if (save) localStorage.setItem('theme', theme);
            $$('.theme-btn').forEach(btn => btn.classList.remove('active'));
            $(`.theme-btn[data-theme="${theme}"]`)?.classList.add('active');
        },
        startAnalysis: async (type, category) => {
            let payload = { meal_category: category };
            handle.openAddMealModal(category);

            if (type === 'image') {
                const input = document.createElement('input');
                input.type = 'file'; input.accept = 'image/*';
                input.onchange = async e => {
                    const file = e.target.files[0];
                    if (!file) { handle.closeModal(selectors.addMealModal); return; }

                    // Sprawdź rozmiar pliku przed kompresją
                    if (file.size > 2 * 1024 * 1024) { // Powyżej 2MB
                        showNotification("Zdjęcie jest duże, zmniejszam jakość...", 'info');
                    }

                    try {
                        // Kompresuj obraz
                        const compressedBlob = await compressImage(file);
                        // Konwertuj skompresowany Blob na base64
                        payload.image_base64 = await toBase64(compressedBlob);

                        $('#manual-text-input').value = "Analizuję zdjęcie...";
                        $('#manual-text-input').disabled = true;
                        $('#manual-analyze-btn').classList.add('hidden');

                        const result = await api.analyze(payload);
                        render.analysisResults(result, category);
                    } catch(err) {
                        $('#analysis-error-container').textContent = `Błąd analizy zdjęcia: ${err.message}`;
                        $('#analysis-error-container').style.display = 'block';
                        $('#manual-text-input').value = "";
                        $('#manual-text-input').disabled = false;
                        $('#manual-analyze-btn').classList.remove('hidden');
                        showNotification(`Błąd analizy zdjęcia: ${err.message}`, 'error');
                    }
                };
                input.click();
            } else if (type === 'voice') {
                handle.startSpeechRecognition(category);
            }
        },
        startSpeechRecognition: (category) => {
            if (state.isListening) return;
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                showNotification('Rozpoznawanie mowy nie jest wspierane.', 'error');
                return;
            }

            const recognition = new SpeechRecognition();
            recognition.lang = 'pl-PL';
            recognition.interimResults = false;
            recognition.continuous = true; // Kluczowa zmiana: nasłuchuj ciągle

            const input = $('#manual-text-input');
            input.placeholder = "Słucham... mów teraz.";
            state.isListening = true;

            let finalTranscript = '';
            recognition.onresult = (event) => {
                let interimTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }
                input.value = finalTranscript + interimTranscript;
            };

            recognition.onerror = (event) => {
                showNotification(`Błąd rozpoznawania mowy: ${event.error}`, 'error');
            };

            recognition.onend = () => {
                state.isListening = false;
                input.placeholder = "Analizuję...";
                // Uruchom analizę po zakończeniu mowy
                if (finalTranscript.trim()) {
                    $('#manual-analyze-btn').click();
                } else {
                    input.placeholder = "np. 2 jajka sadzone";
                }
            };

            recognition.start();

            // Ustaw timeout, który zatrzyma nasłuchiwanie po 3 sekundach ciszy
            let speechTimeout;
            recognition.onspeechstart = () => {
                clearTimeout(speechTimeout);
            };
            recognition.onspeechend = () => {
                speechTimeout = setTimeout(() => {
                    recognition.stop();
                }, 3000); // 3 sekundy ciszy
            };
        },
        // ### START OF REPLACEMENT 2 ###
        recalculateMacros: (sourceElementId, triggerElement) => {
            const sourceInput = $(`#${sourceElementId}`);
            const container = sourceInput.closest('.modal-content');
            if (!sourceInput || !container) return;

            // Zawsze bazuj na czystych, oryginalnych danych z momentu analizy
            const originalResult = JSON.parse(sourceInput.value);
            const originalDeconstruction = originalResult.deconstruction_details || [];
            const ingredientsContainer = container.querySelector('.interactive-ingredients');
            if (!originalResult || !ingredientsContainer) return;

            const baseTotalWeight = originalDeconstruction.reduce((sum, item) => sum + (item.quantity_grams || 0), 0);
            
            // Logika skalowania "w dół" - od wagi całkowitej do składników
            if (triggerElement && triggerElement.id.includes('total-weight-input')) {
                const newTotalWeight = parseFloat(triggerElement.value) || 0;
                if (!isNaN(newTotalWeight) && newTotalWeight >= 0) {
                    const totalWeightFactor = baseTotalWeight > 0 ? newTotalWeight / baseTotalWeight : 0;
                    ingredientsContainer.querySelectorAll('.ingredient-item').forEach((itemElement, index) => {
                        const weightInput = itemElement.querySelector('.ingredient-weight-input');
                        const originalIngredientWeight = originalDeconstruction[index]?.quantity_grams || 0;
                        weightInput.value = Math.round(originalIngredientWeight * totalWeightFactor);
                    });
                }
            }

            // Przeliczenie makro na podstawie aktualnych wartości w polach
            let totalCalories = 0, totalProtein = 0, totalFat = 0, totalCarbs = 0, finalTotalWeight = 0;
            const finalIngredients = [];

            originalDeconstruction.forEach((originalItem, index) => {
                const itemElement = ingredientsContainer.querySelector(`.ingredient-item[data-index="${index}"]`);
                const checkbox = itemElement.querySelector('.ingredient-checkbox');
                const weightInput = itemElement.querySelector('.ingredient-weight-input');
                
                if (checkbox && checkbox.checked && weightInput) {
                    const currentWeight = parseFloat(weightInput.value);
                    if (!isNaN(currentWeight) && currentWeight >= 0) {
                        finalTotalWeight += currentWeight;
                        
                        // Pobierz dane bazowe (na 100g) ze specjalnych atrybutów
                        const kcalPer100g = parseFloat(itemElement.dataset.kcalPer100g) || 0;
                        const proteinPer100g = parseFloat(itemElement.dataset.proteinPer100g) || 0;
                        const fatPer100g = parseFloat(itemElement.dataset.fatPer100g) || 0;
                        const carbsPer100g = parseFloat(itemElement.dataset.carbsPer100g) || 0;

                        const factor = currentWeight / 100.0;
                        const newCalories = kcalPer100g * factor;
                        const newProtein = proteinPer100g * factor;
                        const newFat = fatPer100g * factor;
                        const newCarbs = carbsPer100g * factor;

                        totalCalories += newCalories;
                        totalProtein += newProtein;
                        totalFat += newFat;
                        totalCarbs += newCarbs;
                        
                        finalIngredients.push({ ...originalItem, name: originalItem.name, quantity_grams: currentWeight, calories: newCalories, protein: newProtein, fat: newFat, carbs: newCarbs });
                    }
                }
            });
            
            // Logika skalowania "w górę" - od składników do wagi całkowitej
            if (triggerElement && !triggerElement.id.includes('total-weight-input')) {
                const totalWeightInput = container.querySelector('#analysis-total-weight-input') || container.querySelector('#edit-total-weight-input');
                if(totalWeightInput) totalWeightInput.value = Math.round(finalTotalWeight);
            }

            container.querySelector('#analysis-macros-summary').textContent = `${Math.round(totalCalories)} kcal &middot; B:${Math.round(totalProtein)} T:${Math.round(totalFat)} W:${Math.round(totalCarbs)}`;
            
            // Zapisz zaktualizowane dane do ukrytego pola
            const finalDataForSaving = {
                aggregated_meal: { ...originalResult.aggregated_meal, name: originalResult.aggregated_meal.name, quantity_grams: finalTotalWeight, calories: totalCalories, protein: totalProtein, fat: totalFat, carbs: totalCarbs },
                deconstruction_details: finalIngredients
            };
            sourceInput.value = JSON.stringify(finalDataForSaving);
        },
        // ### END OF REPLACEMENT 2 ###
        addSelectedToJournal: async (e) => {
            const category = selectors.addMealModal.dataset.currentCategory;
            const date = toISODate(state.currentDate);

            // Upewnij się, że przeliczamy makra ostatni raz przed wysłaniem
            handle.recalculateMacros('analysis-original-data', $('#analysis-total-weight-input'));
            
            const finalData = JSON.parse($('#analysis-original-data').value);
            const mealComponent = finalData.aggregated_meal;
            
            let mealContainer = state.summary.meals.find(m => m.category === category);
            if (!mealContainer) {
                mealContainer = await api.createMeal({ date: date, name: category, category: category, time: new Date().toTimeString().split(' ')[0] });
            }

            const entryData = {
                product_name: mealComponent.name,
                calories: mealComponent.calories,
                protein: mealComponent.protein,
                fat: mealComponent.fat,
                carbs: mealComponent.carbs,
                amount: mealComponent.quantity_grams,
                unit: 'g',
                display_quantity_text: `${Math.round(mealComponent.quantity_grams)}g`,
                deconstruction_details: finalData.deconstruction_details,
                is_default_quantity: mealComponent.is_default_quantity
            };
            
            await api.addMealEntry(mealContainer.id, entryData);
            showNotification('Dodano posiłek!', 'success');
            handle.closeModal(selectors.addMealModal);
            await render.dashboard();
        },
        editMealEntry: (entryData) => {
            const modal = selectors.editMealEntryModal;
            pristineRecipeData = entryData.deconstruction_details || [];
            
            const originalResultForRecalc = { aggregated_meal: entryData, deconstruction_details: pristineRecipeData };
            const initialTotalWeight = pristineRecipeData.reduce((sum, item) => sum + (item.quantity_grams || 0), 0);

            const modalTitle = `Edytuj: ${entryData.product_name}`;
            const modalContent = `
                <div class="analysis-summary">
                     <div class="summary-header">
                        <span id="analysis-final-name">${entryData.product_name}</span>
                        <div class="total-weight-editor">
                           (<input type="number" id="edit-total-weight-input" class="total-weight-input" value="${Math.round(initialTotalWeight)}">g)
                        </div>
                    </div>
                    <div class="summary-macros" id="analysis-macros-summary">${Math.round(entryData.calories)} kcal &middot; B:${Math.round(entryData.protein)} T:${Math.round(entryData.fat)} W:${Math.round(entryData.carbs)}</div>
                </div>
                <div class="ingredients-toggle open">
                    <span>Składniki</span>
                    <i data-feather="chevron-down" class="collapse-icon"></i>
                </div>
                <div class="meal-item-ingredients open">
                    ${templates.interactiveIngredientList(pristineRecipeData, true)}
                </div>
                <input type="hidden" id="edit-original-data" value='${JSON.stringify(originalResultForRecalc)}'>
            `;
            
            render.modal(modalTitle, modalContent, true, modal);
            
            handle.recalculateMacros('edit-original-data', modal.querySelector('.total-weight-input'));
            
            const container = modal.querySelector('#edit-meal-entry-modal-body');
            const newContainer = container.cloneNode(true);
            container.parentNode.replaceChild(newContainer, container);
            
            newContainer.addEventListener('input', (e) => {
                 if (e.target.classList.contains('total-weight-input') || e.target.classList.contains('ingredient-weight-input') || e.target.classList.contains('ingredient-checkbox')) {
                    handle.recalculateMacros('edit-original-data', e.target);
                }
            });
            
            const saveBtn = modal.querySelector('#save-edit-entry-btn');
            const newSaveBtn = saveBtn.cloneNode(true);
            saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);

            newSaveBtn.addEventListener('click', async () => {
                handle.recalculateMacros('edit-original-data', newContainer.querySelector('.total-weight-input'));
                const finalData = JSON.parse(newContainer.querySelector('#edit-original-data').value);
                const mealComponent = finalData.aggregated_meal;
                
                const updatedEntryData = {
                    product_name: mealComponent.product_name || mealComponent.name,
                    calories: mealComponent.calories, protein: mealComponent.protein,
                    fat: mealComponent.fat, carbs: mealComponent.carbs,
                    amount: mealComponent.quantity_grams, unit: 'g',
                    display_quantity_text: `${Math.round(mealComponent.quantity_grams)}g`,
                    deconstruction_details: finalData.deconstruction_details,
                    is_default_quantity: mealComponent.is_default_quantity
                };

                await api.updateMealEntry(entryData.id, updatedEntryData);
                showNotification('Wpis zaktualizowany!', 'success');
                handle.closeModal(modal);
                await render.dashboard();
            });
        },
        saveSettings: async () => {
            const modal = selectors.settingsModal;
            const updateData = {};
            const activeTab = modal.querySelector('.tab-link.active').dataset.tab;

            if (activeTab === 'tab-profile') {
                updateData.name = modal.querySelector('#profile-name').value.trim();
                updateData.date_of_birth = modal.querySelector('#profile-dob').value || null;
                updateData.gender = modal.querySelector('#profile-gender').value;
                updateData.height = parseFloat(modal.querySelector('#profile-height').value) || null;
                updateData.weight = parseFloat(modal.querySelector('#profile-weight').value) || null;
            } else if (activeTab === 'tab-goals') {
                updateData.target_weight = parseFloat(modal.querySelector('#profile-target-weight').value) || null;
                updateData.weekly_goal_kg = parseFloat(modal.querySelector('#weekly-goal-slider').value);
                updateData.activity_level = modal.querySelector('#profile-activity').value;
                updateData.diet_style = modal.querySelector('#profile-diet').value;
                updateData.add_workout_calories_to_goal = modal.querySelector('#add-workout-calories-toggle').checked;

                const calories = parseInt(modal.querySelector('#profile-calories').value) || 0;
                const sliders = $$('.macro-slider');
                const proteinPerc = parseInt(sliders[0].value) || 0;
                const fatPerc = parseInt(sliders[1].value) || 0;
                const carbPerc = parseInt(sliders[2].value) || 0;

                updateData.calorie_goal = calories;
                updateData.protein_goal = Math.round((calories * proteinPerc / 100) / 4);
                updateData.fat_goal = Math.round((calories * fatPerc / 100) / 9);
                updateData.carb_goal = Math.round((calories * carbPerc / 100) / 4);
                updateData.protein_goal_perc = proteinPerc;
                updateData.fat_goal_perc = fatPerc;
                updateData.carb_goal_perc = carbPerc;

            } else if (activeTab === 'tab-tastes') {
                const prefs = { proteins: [], carbs: [], fats: [] };
                modal.querySelectorAll('.sortable-list').forEach(list => {
                    const category = list.dataset.category;
                    prefs[category] = Array.from(list.querySelectorAll('li span')).map(span => span.textContent);
                });
                updateData.preferences = prefs;
            } else if (activeTab === 'tab-app') {
                updateData.is_social_profile_active = modal.querySelector('#social-profile-toggle').checked;
            }

            try {
                const updatedUser = await api.updateMe(updateData);
                state.currentUser = updatedUser;
                showNotification('Ustawienia zapisane!', 'success');
                render.dashboard();
                if (state.activeView === 'social') render.view('social');
            } catch (error) { console.error("Błąd zapisu ustawień:", error); }
        },
        switchSettingsTab: (tabId) => {
            $$('#settings-modal .tab-link').forEach(t => t.classList.remove('active'));
            $(`#settings-modal .tab-link[data-tab="${tabId}"]`).classList.add('active');
            let content = '';
            if(tabId === 'tab-profile') content = templates.settingsProfile(state.currentUser);
            if(tabId === 'tab-goals') content = templates.settingsGoals(state.currentUser);
            if(tabId === 'tab-tastes') content = templates.settingsTastes(state.currentUser.preferences);
            if(tabId === 'tab-app') content = templates.settingsApp(state.currentUser);
            render.modal('Ustawienia', content, true, selectors.settingsModal); // Przekazano modalElement
            featherReplace();
            // KLUCZOWA ZMIANA: Inicjalizacja SortableJS po załadowaniu zakładki "Twoje Smaki"
            if(tabId === 'tab-tastes') makeListsSortable();
            if(tabId === 'tab-goals') addGoalsEventListeners();
            if(tabId === 'tab-app') addAppSettingsEventListeners();
        },
        generateDietPlan: async () => {
            const container = $('#diet-plan-container');
            container.innerHTML = '<div class="spinner-container"><div class="spinner"></div><p>AI Chef gotuje...</p></div>';
            try {
                const plan = await api.getDietPlan();
                // Plan jest już listą obiektów, więc można go bezpośrednio stringify
                state.currentUser.last_diet_plan = JSON.stringify(plan); 
                render.dietPlan(plan);

                // Odśwież dane użytkownika, aby zaktualizować diet_plan_requests
                const updatedUser = await api.getMe();
                state.currentUser.diet_plan_requests = updatedUser.diet_plan_requests;
                const requestsLeft = 3 - (state.currentUser.diet_plan_requests || 0);
                const generateBtn = $('#generate-diet-plan-btn');
                if (generateBtn) {
                    generateBtn.querySelector('span').textContent = `Wygeneruj Plan Dnia (${requestsLeft}/3)`;
                    generateBtn.disabled = requestsLeft <= 0;
                }
            } catch(error) {
                 container.innerHTML = `<p class="empty-list error-message">${error.message}</p>`;
            }
        },
        showDetailsModal: (entry) => {
            const modal = selectors.detailsModal;
            modal.querySelector('h3').textContent = `Składniki: ${entry.product_name}`;
            const body = modal.querySelector('#details-modal-body');

            // Sprawdź, czy dekonstrukcja już istnieje i ma składniki
            if (entry.deconstruction_details && entry.deconstruction_details.length > 0) {
                // Jeśli tak, po prostu je wyświetl
                body.innerHTML = entry.deconstruction_details.map(item => `
                    <div class="meal-item">
                        <div class="meal-info">
                            <span>${item.name} (${item.display_quantity_text})</span>
                            <span class="meal-macros">${Math.round(item.calories)} kcal &middot; B:${Math.round(item.protein)} T:${Math.round(item.fat)} W:${Math.round(item.carbs)}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                // Jeśli nie, pokaż przycisk do dekonstrukcji
                body.innerHTML = `
                    <div class="deconstruct-prompt">
                        <p>Szczegółowe składniki nie zostały jeszcze wygenerowane.</p>
                        <button id="generate-deconstruction-btn" class="primary-btn" data-entry-id="${entry.id}">
                            <i data-feather="cpu"></i>
                            <span>Analizuj składniki</span>
                        </button>
                    </div>
                `;
                featherReplace();
            }
            
            modal.classList.remove('hidden');
        },
        generateAnalysis: async () => {
            const startDateStr = selectors.analysisStartDate.value;
            const endDateStr = selectors.analysisEndDate.value;

            if (!startDateStr || !endDateStr) {
                return showNotification('Wybierz datę początkową i końcową.', 'error');
            }

            const startDate = new Date(startDateStr);
            const endDate = new Date(endDateStr);

            if (startDate > endDate) {
                return showNotification('Data początkowa nie może być późniejsza niż data końcowa.', 'error');
            }

            selectors.aiCoachContainer.classList.remove('hidden');
            selectors.aiCoachSummary.innerHTML = '<div class="spinner-container"><div class="spinner"></div><p>Generuję Twoje podsumowanie AI...</p></div>';

            try {
                const summary = await api.generateWeeklyAnalysis(startDateStr, endDateStr);
                // Po udanym wygenerowaniu, odśwież dane użytkownika, aby pobrać nową datę `last_analysis_generated_at`
                state.currentUser = await api.getMe();

                state.analysis.aiSummary = summary.ai_coach_summary;
                state.analysis.generatedAt = state.currentUser.last_analysis_generated_at ? new Date(state.currentUser.last_analysis_generated_at) : null; // Upewnij się, że to jest Date obiekt
                state.analysis.startDate = new Date(summary.analysis_start_date);
                state.analysis.endDate = new Date(summary.analysis_end_date);

                // Odśwież widok z nowymi danymi
                render.renderAnalysisContent(state.analysisRange.data, state.analysis.aiSummary);

            } catch (error) {
                // Błąd zostanie wyświetlony przez globalny handler w `api.request`
                selectors.aiCoachSummary.innerHTML = `<p class="error-message">Nie można wygenerować analizy. ${error.message}</p>`;
                state.analysis.aiSummary = null; // Wyczyść stare podsumowanie w razie błędu
            } finally {
                // Zawsze aktualizuj stan przycisku po próbie generacji
                handle.updateAnalysisButtonState();
            }
        },
        updateAnalysisButtonState: () => {
            const generateBtn = selectors.generateAnalysisBtn;
            if (!generateBtn) return;

            const lastGenDate = state.currentUser.last_analysis_generated_at ? new Date(state.currentUser.last_analysis_generated_at) : null;

            if (lastGenDate) {
                const timeDiff = new Date().getTime() - lastGenDate.getTime();
                const hoursSinceLastGeneration = timeDiff / (1000 * 60 * 60);
                if (hoursSinceLastGeneration < 24) {
                    const remainingHours = Math.ceil(24 - hoursSinceLastGeneration);
                    generateBtn.disabled = true;
                    generateBtn.querySelector('span').textContent = `Dostępne za ${remainingHours}h`;
                    // Upewnij się, że timer jest resetowany, aby uniknąć wielu timerów
                    if (generateBtn._timer) clearTimeout(generateBtn._timer);
                    // Sprawdzaj co godzinę, czy można już odblokować
                    generateBtn._timer = setTimeout(() => handle.updateAnalysisButtonState(), 3600 * 1000);
                } else {
                    generateBtn.disabled = false;
                    generateBtn.querySelector('span').textContent = 'Uruchom Analizę AI';
                }
            } else {
                generateBtn.disabled = false;
                generateBtn.querySelector('span').textContent = 'Uruchom Analizę AI';
            }
        },
        setAnalysisDateRange: async (days) => {
            const endDate = new Date(state.currentDate);
            endDate.setHours(0,0,0,0);
            let startDate = new Date(endDate);

            if (days !== null) {
                startDate.setDate(endDate.getDate() - (days - 1));
            } else {
                // Jeśli days jest null, oznacza to ręczną zmianę dat w inputach
                startDate = new Date(selectors.analysisStartDate.value);
                endDate = new Date(selectors.analysisEndDate.value);
            }

            selectors.analysisStartDate.value = toISODate(startDate);
            selectors.analysisEndDate.value = toISODate(endDate);

            state.analysisRange.startDate = startDate;
            state.analysisRange.endDate = endDate;

            try {
                const dataForCharts = await api.getAnalysisData(toISODate(startDate), toISODate(endDate));
                state.analysisRange.data = dataForCharts;
                render.renderAnalysisContent(dataForCharts, state.analysis.aiSummary);
            } catch (error) {
                state.analysisRange.data = null;
                render.renderAnalysisContent(null, state.analysis.aiSummary);
            }
        },
        sendMessage: async (e) => {
            e.preventDefault();
            const input = $('#chat-input');
            const messageText = input.value.trim();
            if (!messageText || !state.chat.activeConversationId) return;

            const messagesContainer = $('.chat-messages');
            messagesContainer.innerHTML += templates.chatMessage({ role: 'user', content: messageText });
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            input.value = '';
            input.disabled = true;
            messagesContainer.innerHTML += `<div class="chat-message ai"><div class="message-bubble is-typing"><span></span><span></span><span></span></div></div>`;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            try {
                const response = await api.sendMessageToConversation(state.chat.activeConversationId, messageText);
                $('.chat-message.ai .is-typing').parentElement.remove();
                messagesContainer.innerHTML += templates.chatMessage(response);
            } catch (error) {
                $('.chat-message.ai .is-typing')?.parentElement.remove();
                messagesContainer.innerHTML += templates.chatMessage({ role: 'ai', content: 'Przepraszam, wystąpił błąd.' });
            } finally {
                input.disabled = false;
                input.focus();
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        },
        clearChatHistory: async () => {
            const confirmClear = await new Promise(resolve => {
                const modalHtml = `
                    <div id="confirm-modal" class="modal-overlay">
                        <div class="modal-content small">
                            <h3>Potwierdź</h3>
                            <p>Czy na pewno chcesz wyczyścić historię rozmowy?</p>
                            <div class="modal-footer" style="justify-content: space-around;">
                                <button id="cancel-clear-btn" class="secondary-btn">Anuluj</button>
                                <button id="confirm-clear-btn" class="danger-btn">Wyczyść</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHtml);
                const confirmModal = $('#confirm-modal');
                $('#confirm-clear-btn').addEventListener('click', () => { confirmModal.remove(); resolve(true); });
                $('#cancel-clear-btn').addEventListener('click', () => { confirmModal.remove(); resolve(false); });
                confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) { confirmModal.remove(); resolve(false); } });
            });

            if (confirmClear) {
                try { 
                    // Użyj aktywnej konwersacji do usunięcia
                    await api.deleteConversation(state.chat.activeConversationId); 
                    showNotification('Historia czatu wyczyszczona.', 'success'); 
                    // Po usunięciu, odśwież czat, co spowoduje załadowanie nowych konwersacji lub utworzenie nowej
                    render.chat(); 
                }
                catch (error) { showNotification('Nie udało się wyczyścić historii.', 'error'); }
            }
        },
        addWorkout: () => {
            const category = 'Trening';
            render.modal(`Dodaj ${category}`, templates.manualInput, false);
            $('#manual-text-input').placeholder = 'np. 30 minut biegania';

            const analyzeBtn = $('#manual-analyze-btn');
            if(analyzeBtn) analyzeBtn.textContent = 'Dodaj Trening';

            analyzeBtn.replaceWith(analyzeBtn.cloneNode(true));
            $('#manual-analyze-btn').addEventListener('click', async () => {
                const text = $('#manual-text-input').value.trim();
                const errorContainer = $('#analysis-error-container');
                errorContainer.style.display = 'none';

                if (!text) {
                    errorContainer.textContent = 'Wpisz opis treningu.';
                    errorContainer.style.display = 'block';
                    return;
                }

                try {
                    await api.addWorkout({ text: text, date: toISODate(state.currentDate) });
                    showNotification('Trening dodany!', 'success');
                    handle.closeModal(selectors.addMealModal);
                    render.dashboard();
                } catch (err) {
                    errorContainer.textContent = err.message;
                    errorContainer.style.display = 'block';
                }
            });
        },
        social: {
            search: debounce(async (query) => {
                const resultsContainer = $('#user-search-results');
                resultsContainer.innerHTML = ''; // Wyczyść poprzednie wyniki i błędy
                if (query.length < 3) { return; } // Nie wyszukuj dla zbyt krótkich zapytań
                
                resultsContainer.innerHTML = '<div class="spinner-container"><div class="spinner"></div></div>'; // Pokaż spinner
                
                try {
                    const users = await api.searchUsers(query);
                    state.social.searchResults = users;
                    resultsContainer.innerHTML = users.length > 0 ? users.map(templates.userSearchResultItem).join('') : '<p class="empty-list-small">Brak wyników.</p>';
                    featherReplace();
                } catch (error) 
                    { resultsContainer.innerHTML = `<p class="error-message">Błąd wyszukiwania: ${error.message}</p>`; // Wyświetl szczegóły błędu
                }
            }, 500),
            addFriend: async (userId) => {
                try {
                    await api.sendFriendRequest(userId);
                    showNotification('Wysłano zaproszenie!', 'success');
                    const query = $('#user-search-input').value;
                    if (query.length >= 3) handle.social.search(query); // Odśwież wyniki wyszukiwania
                } catch (error) { showNotification(`Błąd wysyłania zaproszenia: ${error.message}`, 'error'); }
            },
            respondToRequest: async (friendshipId, status) => {
                try {
                    await api.respondToRequest(friendshipId, status);
                    showNotification(`Zaproszenie ${status === 'accepted' ? 'zaakceptowane' : 'odrzucone'}.`, 'success');
                    render.social(); // Odśwież widok społecznościowy
                } catch (error) { showNotification(`Błąd odpowiedzi na zaproszenie: ${error.message}`, 'error'); }
            },
            removeFriend: async (friendId) => {
                const confirmRemove = await new Promise(resolve => {
                    const modalHtml = `<div id="confirm-modal" class="modal-overlay"><div class="modal-content small"><h3>Potwierdź</h3><p>Czy na pewno chcesz usunąć tego znajomego?</p><div class="modal-footer" style="justify-content: space-around;"><button id="cancel-remove-btn" class="secondary-btn">Anuluj</button><button id="confirm-remove-btn" class="danger-btn">Usuń</button></div></div></div>`;
                    document.body.insertAdjacentHTML('beforeend', modalHtml);
                    const confirmModal = $('#confirm-modal');
                    $('#confirm-remove-btn').addEventListener('click', () => { confirmModal.remove(); resolve(true); });
                    $('#cancel-remove-btn').addEventListener('click', () => { confirmModal.remove(); resolve(false); });
                    confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) { confirmModal.remove(); resolve(false); } });
                });

                if (confirmRemove) {
                    try {
                        await api.deleteFriend(friendId);
                        showNotification('Znajomy usunięty.', 'success');
                        render.social(); // Odśwież widok społecznościowy
                    } catch (error) { showNotification(`Błąd usuwania znajomego: ${error.message}`, 'error'); }
                }
            }
        }
    };

    // === LISTENERY (bez zmian) ===
    async function addMainAppEventListeners() {
        selectors.appContainer.addEventListener('click', async e => {
            const navBtn = e.target.closest('.nav-btn');
            if (navBtn) return render.view(navBtn.dataset.view);

            const settingsBtn = e.target.closest('#settings-btn');
            if (settingsBtn) return handle.openSettingsModal();
            
            // NOWE: Listener dla przycisku edycji wpisu (przeniesiony wyżej)
            const editEntryBtn = e.target.closest('.edit-meal-entry-btn');
            if(editEntryBtn) {
                e.stopPropagation();
                const entryData = JSON.parse(editEntryBtn.dataset.entry);
                handle.editMealEntry(entryData); 
                return;
            }

            // Listener dla przycisku usuwania wpisu (przeniesiony wyżej)
            const deleteEntryBtn = e.target.closest('.delete-meal-entry-btn');
            if(deleteEntryBtn) {
                const confirmDelete = await new Promise(resolve => {
                    const modalHtml = `<div id="confirm-modal" class="modal-overlay"><div class="modal-content small"><h3>Potwierdź</h3><p>Na pewno usunąć ten produkt?</p><div class="modal-footer" style="justify-content: space-around;"><button id="cancel-delete-btn" class="secondary-btn">Anuluj</button><button id="confirm-delete-btn" class="danger-btn">Usuń</button></div></div></div>`;
                    document.body.insertAdjacentHTML('beforeend', modalHtml);
                    const confirmModal = $('#confirm-modal');
                    $('#confirm-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(true); });
                    $('#cancel-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(false); });
                    confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) { confirmModal.remove(); resolve(false); } });
                });

                if(confirmDelete) {
                    await api.deleteMealEntry(deleteEntryBtn.dataset.id);
                    await render.dashboard();
                }
                return;
            }

            // Listener dla rozwijania/zwijania składników
            const mealItemToggle = e.target.closest('.meal-item-toggle');
            if (mealItemToggle) {
                const mealItem = mealItemToggle.closest('.meal-item');
                const ingredientsList = mealItem.querySelector('.meal-item-ingredients');
                if (ingredientsList) {
                    mealItemToggle.classList.toggle('open');
                    ingredientsList.classList.toggle('open');
                }
                return;
            }

            const waterBtn = e.target.closest('.water-btn');
            if (waterBtn) {
                waterBtn.disabled = true;
                const amount = parseInt(waterBtn.dataset.amount);
                if (amount < 0 && state.summary.water_consumed + amount < 0) {
                    showNotification('Nie możesz odjąć więcej wody niż masz!', 'error');
                    waterBtn.disabled = false;
                    return;
                }
                await api.addWater({ amount: amount, date: toISODate(state.currentDate), time: new Date().toTimeString().split(' ')[0] });
                await render.dashboard();
                return;
            }

            const generatePlanBtn = e.target.closest('#generate-diet-plan-btn');
            if (generatePlanBtn) return handle.generateDietPlan();

            const mealBtn = e.target.closest('.add-meal-btn');
            if(mealBtn) {
                e.stopPropagation();
                handle.startAnalysis(mealBtn.dataset.type, mealBtn.dataset.category);
                return;
            }

            const deleteWorkoutBtn = e.target.closest('.delete-workout-btn');
            if(deleteWorkoutBtn) {
                const confirmDelete = await new Promise(resolve => {
                    const modalHtml = `<div id="confirm-modal" class="modal-overlay"><div class="modal-content small"><h3>Potwierdź</h3><p>Na pewno usunąć ten trening?</p><div class="modal-footer" style="justify-content: space-around;"><button id="cancel-delete-btn" class="secondary-btn">Anuluj</button><button id="confirm-delete-btn" class="danger-btn">Usuń</button></div></div></div>`;
                    document.body.insertAdjacentHTML('beforeend', modalHtml);
                    const confirmModal = $('#confirm-modal');
                    $('#confirm-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(true); });
                    $('#cancel-delete-btn').addEventListener('click', () => { confirmModal.remove(); resolve(false); });
                    confirmModal.addEventListener('click', (e) => { if (e.target === confirmModal) { confirmModal.remove(); resolve(false); } });
                });

                if(confirmDelete) {
                    await api.deleteWorkout(deleteWorkoutBtn.dataset.id);
                    await render.dashboard();
                }
                return;
            }

            const addWorkoutBtn = e.target.closest('.add-workout-btn');
            if(addWorkoutBtn) {
                e.stopPropagation();
                handle.addWorkout();
                return;
            }

            const collapsibleHeader = e.target.closest('.collapsible');
             if (collapsibleHeader) {
                const list = $(collapsibleHeader.dataset.targetList);
                collapsibleHeader.classList.toggle('open');
                list.classList.toggle('collapsed');
                return;
            }

            const infoBtn = e.target.closest('.info-btn');
            if (infoBtn) {
                const entryId = parseInt(infoBtn.dataset.entryId, 10);
                if (!entryId) return;

                let entryToShow = null;
                // Znajdź pełny obiekt wpisu w stanie aplikacji
                for (const meal of state.summary.meals) {
                    const foundEntry = meal.entries.find(e => e.id === entryId);
                    if (foundEntry) {
                        entryToShow = foundEntry;
                        break;
                    }
                }

                if (entryToShow) {
                    // Przekaż cały obiekt wpisu do funkcji
                    handle.showDetailsModal(entryToShow);
                } else {
                    showNotification('Nie znaleziono szczegółów tego wpisu.', 'error');
                }
                return;
            }

            const dateEl = e.target.closest('#current-date, #prev-day-btn, #next-day-btn');
            if (dateEl) {
                if (dateEl.id === 'current-date') return handle.openCalendarModal();
                if (dateEl.id === 'prev-day-btn') return handle.changeDate(-1);
                if (dateEl.id === 'next-day-btn') return handle.changeDate(1);
            }

            const goToSettingsBtn = e.target.closest('#go-to-settings-btn');
            if (goToSettingsBtn) {
                handle.openSettingsModal();
                setTimeout(() => handle.switchSettingsTab('tab-app'), 100);
            }
        });

        // Obsługa zamykania modali po kliknięciu poza ich zawartością lub na przycisk zamykający
        [selectors.addMealModal, selectors.settingsModal, selectors.calendarModal, selectors.detailsModal, selectors.editMealEntryModal].forEach(modal => { // NOWE: Dodano editMealEntryModal
             modal.addEventListener('click', e => {
                // Sprawdź, czy kliknięto bezpośrednio na overlay lub na przycisk zamykający
                if (e.target === modal || e.target.closest('.modal-close-btn')) {
                    handle.closeModal(modal);
                }
            });
        });

        // Listener dla modala szczegółów (dekonstrukcja na żądanie)
        selectors.detailsModal.addEventListener('click', async e => {
            const deconstructBtn = e.target.closest('#generate-deconstruction-btn');
            if (deconstructBtn) {
                const entryId = deconstructBtn.dataset.entryId;
                const body = selectors.detailsModal.querySelector('#details-modal-body');
                body.innerHTML = '<div class="spinner-container"><div class="spinner"></div><p>Analizuję...</p></div>';

                try {
                    // Zmieniono wywołanie API na nowy endpoint
                    const details = await api.analyze({ entry_id: entryId, meal_category: 'deconstruct' }); // Używamy endpointu /analysis/meal z parametrem entry_id
                    // Po udanej dekonstrukcji, odświeżamy cały dashboard,
                    // aby zaktualizować stan i pokazać nowe dane
                    await render.dashboard(); 
                    
                    // Ponownie otwieramy modal, który teraz pokaże listę składników
                    const updatedEntry = state.summary.meals
                        .flatMap(m => m.entries)
                        .find(entry => entry.id == entryId);
                    
                    if (updatedEntry) {
                        handle.showDetailsModal(updatedEntry);
                    } else {
                        handle.closeModal(selectors.detailsModal);
                    }

                } catch (error) {
                    // Sprawdzamy, czy błąd zawiera nasz specjalny kod statusu 409
                    if (error.message && error.message.includes('409')) {
                        body.innerHTML = `<p class="info-message">To jest produkt podstawowy i nie wymaga analizy składników.</p>`;
                    } else {
                        body.innerHTML = `<p class="error-message">AI nie było w stanie rozbić tego produktu na składniki.</p>`;
                    }
                }
            }
        });
    }

    function addAuthEventListeners() {
        $('#login-form')?.addEventListener('submit', handle.login);
        $('#register-form')?.addEventListener('submit', handle.register);
        $('#forgot-password-form')?.addEventListener('submit', handle.forgotPassword);
        
        selectors.authContainer.addEventListener('click', e => {
            if (e.target.id === 'show-login') handle.showLoginForm(e);
            if (e.target.id === 'show-register') handle.showRegisterForm(e);
            if (e.target.id === 'show-forgot-password') handle.showForgotPasswordForm(e);
        });
    }

    function addManualInputListeners(category) {
        $('#manual-analyze-btn')?.addEventListener('click', async () => {
            // Odczytujemy kategorię bezpośrednio z okna modalnego
            const category = selectors.addMealModal.dataset.currentCategory;
            const text = $('#manual-text-input').value.trim();
            const errorContainer = $('#analysis-error-container');
            const resultsContainer = $('#analysis-results-container');
            errorContainer.style.display = 'none';
            resultsContainer.innerHTML = '';

            if (!text) {
                errorContainer.textContent = 'Wpisz tekst do analizy.';
                errorContainer.style.display = 'block';
                return;
            }

            resultsContainer.innerHTML = '<div class="spinner-container"><div class="spinner"></div></div>';

            try {
                const result = await api.analyze({ text, meal_category: category });
                render.analysisResults(result, category);
            } catch (err) {
                resultsContainer.innerHTML = '';
                errorContainer.textContent = err.message;
                errorContainer.style.display = 'block';
            }
        });
        selectors.addMealModal.querySelector('#add-selected-to-journal-btn')?.addEventListener('click', handle.addSelectedToJournal);
    }

    function addCalendarModalEventListeners() {
        const modalBody = $('#calendar-modal-body');
        modalBody.addEventListener('click', e => {
            const dayTarget = e.target.closest('.calendar-day');
            const prevMonthTarget = e.target.closest('#calendar-prev-month');
            const nextMonthTarget = e.target.closest('#calendar-next-month');

            if(dayTarget && !dayTarget.classList.contains('other-month')) {
                state.currentDate.setDate(parseInt(dayTarget.dataset.day));
                handle.closeModal(selectors.calendarModal);
                render.dashboard();
            } else if (prevMonthTarget) {
                state.currentDate.setMonth(state.currentDate.getMonth() - 1);
                modalBody.innerHTML = render.calendar();
                featherReplace();
            } else if (nextMonthTarget) {
                state.currentDate.setMonth(state.currentDate.getMonth() + 1);
                modalBody.innerHTML = render.calendar();
                featherReplace();
            }
        });
    }

    function addSettingsEventListeners() {
        const modal = selectors.settingsModal;
        modal.querySelector('.tabs').addEventListener('click', e => {
            if (e.target.classList.contains('tab-link')) handle.switchSettingsTab(e.target.dataset.tab);
        });
        modal.querySelector('#save-settings-btn').addEventListener('click', handle.saveSettings);

        // Obsługa dodawania nowego elementu do listy preferencji
        modal.addEventListener('submit', e => {
             if(e.target.classList.contains('add-pref-form')) {
                e.preventDefault();
                const category = e.target.dataset.category;
                const input = e.target.querySelector('input');
                const value = input.value.trim();
                if(value) {
                    const list = $(`#taste-${category}`);
                    list.insertAdjacentHTML('beforeend', `<li><i data-feather="menu" class="drag-handle"></i><span>${value}</span><button class="delete-pref-item icon-btn"><i data-feather="x"></i></button></li>`);
                    input.value = '';
                    featherReplace();
                    // Ponowna inicjalizacja SortableJS po dodaniu nowego elementu
                    makeListsSortable(); 
                }
             }
        });
        // Obsługa usuwania elementu z listy preferencji
        modal.addEventListener('click', e => {
            if (e.target.closest('.delete-pref-item')) {
                e.target.closest('li').remove();
            }
        });
    }

    function addGoalsEventListeners() {
        const settingsBody = $('#settings-body');
        if (!settingsBody) return;

        const updateEtaDisplay = () => {
            // KRYTYCZNA POPRAWKA: Używamy wagi ze stanu aplikacji, a nie z pola formularza
            const weight = state.currentUser.weight; 
            const targetWeight = parseFloat($('#profile-target-weight')?.value);
            const weeklyGoalKg = parseFloat($('#weekly-goal-slider')?.value);
            const etaDisplay = $('#goal-eta-display');

            if (!etaDisplay || !weight || !targetWeight || weeklyGoalKg === 0) {
                etaDisplay.textContent = '';
                return;
            }

            const weightToChange = weight - targetWeight;

            if ((weeklyGoalKg < 0 && weightToChange <= 0) || (weeklyGoalKg > 0 && weightToChange >= 0)) {
                etaDisplay.textContent = 'Cel już osiągnięty lub błędny kierunek.';
                return;
            }

            const weeksToGoal = Math.abs(weightToChange / weeklyGoalKg);
            const daysToGoal = Math.floor(weeksToGoal * 7);
            
            if (daysToGoal > 365 * 10) {
                 etaDisplay.textContent = 'Cel bardzo odległy w czasie.';
                 return;
            }

            const etaDate = new Date();
            etaDate.setDate(etaDate.getDate() + daysToGoal);
            etaDisplay.textContent = `Szacowana data osiągnięcia celu: ${etaDate.toLocaleDateString('pl-PL')}`;
        };

        settingsBody.addEventListener('input', e => {
            const targetId = e.target.id;
            if (targetId === 'weekly-goal-slider') {
                e.target.nextElementSibling.textContent = `${parseFloat(e.target.value).toFixed(1)} kg`;
                updateEtaDisplay();
            }
            if (targetId === 'profile-target-weight') {
                updateEtaDisplay();
            }
            if (e.target.classList.contains('macro-slider') || targetId === 'profile-calories') {
                updateMacroCalculations();
            }
        });

        $('#suggest-ai-goals-btn')?.addEventListener('click', async () => {
            const requestData = {
                gender: state.currentUser.gender,
                date_of_birth: state.currentUser.date_of_birth,
                height: state.currentUser.height,
                weight: state.currentUser.weight, // Używamy wagi ze stanu
                activity_level: $('#profile-activity').value,
                weekly_goal_kg: parseFloat($('#weekly-goal-slider').value),
                diet_style: $('#profile-diet').value,
            };

            if (!requestData.gender || !requestData.date_of_birth || !requestData.height || !requestData.weight) {
                return showNotification('Uzupełnij dane w Profilu, aby AI zasugerowało cele.', 'error');
            }

            try {
                const suggested = await api.suggestGoals(requestData);
                $('#profile-calories').value = suggested.calorie_goal;
                const totalCalories = suggested.calorie_goal;
                const proteinGrams = suggested.protein_goal;
                const fatGrams = suggested.fat_goal;
                const proteinPerc = Math.round(((proteinGrams * 4) / totalCalories) * 100);
                const fatPerc = Math.round(((fatGrams * 9) / totalCalories) * 100);
                const carbPerc = 100 - proteinPerc - fatPerc;
                $('.macro-slider[data-macro="p"]').value = proteinPerc;
                $('.macro-slider[data-macro="f"]').value = fatPerc;
                $('.macro-slider[data-macro="c"]').value = carbPerc;
                updateMacroCalculations();
                updateEtaDisplay();
                showNotification('AI zasugerowało nowe cele!', 'success');
            }
            catch(e) { /* błąd obsłużony w api.request */ }
        });

        updateEtaDisplay();
    }

    function addAppSettingsEventListeners() {
        const currentTheme = localStorage.getItem('theme') || 'system';
        handle.themeChange(currentTheme, false);

        $('#logout-btn')?.addEventListener('click', handle.logout);
        $('#delete-account-btn')?.addEventListener('click', handle.deleteAccount);
        $$('.theme-btn').forEach(btn => {
            btn.addEventListener('click', (e) => handle.themeChange(e.currentTarget.dataset.theme));
        });
    }

    function addChatEventListeners() {
        const chatForm = $('#chat-form');
        const newChatBtn = $('#new-chat-btn');
        const conversationsList = $('#conversations-list');

        if (chatForm) chatForm.onsubmit = handle.sendMessage;
        if (newChatBtn) newChatBtn.onclick = async () => {
            try {
                const newConvo = await api.createConversation();
                state.chat.activeConversationId = newConvo.id;
                await render.chat();
            } catch(e) { /* błąd obsłużony globalnie */ }
        };
        
        if (conversationsList) conversationsList.onclick = async (e) => {
            const convoItem = e.target.closest('.conversation-item');
            const pinBtn = e.target.closest('.pin-convo-btn');
            const deleteBtn = e.target.closest('.delete-convo-btn');

            if (deleteBtn) {
                e.stopPropagation();
                const convoId = parseInt(deleteBtn.closest('.conversation-item').dataset.id);
                if (confirm('Czy na pewno chcesz usunąć tę rozmowę?')) {
                    try {
                        await api.deleteConversation(convoId);
                        if (state.chat.activeConversationId === convoId) {
                            state.chat.activeConversationId = null;
                        }
                        await render.chat();
                        showNotification('Rozmowa usunięta.', 'success');
                    } catch (err) { /* błąd obsłużony globalnie */ }
                }
            } else if (pinBtn) {
                e.stopPropagation();
                const convoId = parseInt(pinBtn.closest('.conversation-item').dataset.id);
                try {
                    await api.pinConversation(convoId);
                    await render.chat();
                } catch (err) { /* błąd obsłużony globalnie */ }
            } else if (convoItem) {
                const newActiveId = parseInt(convoItem.dataset.id);
                if (state.chat.activeConversationId !== newActiveId) {
                    state.chat.activeConversationId = newActiveId;
                    await render.chat();
                }
            }
        };
    }

    function addSocialEventListeners() {
        $('#user-search-input')?.addEventListener('input', (e) => handle.social.search(e.target.value));
        $('#social-content')?.addEventListener('click', async (e) => {
            const addBtn = e.target.closest('.add-friend-btn');
            if (addBtn) {
                addBtn.disabled = true;
                await handle.social.addFriend(parseInt(addBtn.dataset.id));
                return;
            }

            const respondBtn = e.target.closest('.respond-request-btn');
            if (respondBtn) {
                const item = respondBtn.closest('.social-item');
                item.querySelectorAll('button').forEach(b => b.disabled = true);
                const friendshipId = parseInt(item.dataset.id);
                const status = respondBtn.dataset.status;
                await handle.social.respondToRequest(friendshipId, status);
                return;
            }

            const removeBtn = e.target.closest('.remove-friend-btn');
            if (removeBtn) {
                const friendId = parseInt(removeBtn.closest('.social-item').dataset.id);
                await handle.social.removeFriend(friendId);
                return;
            }

            // DODAJ TEN NOWY BLOK PONIŻEJ
            const joinBtn = e.target.closest('.join-challenge-btn');
            if (joinBtn) {
                joinBtn.disabled = true;
                joinBtn.textContent = 'Dołączanie...';
                const challengeId = parseInt(joinBtn.dataset.id);
                try {
                    await api.joinChallenge(challengeId);
                    showNotification('Dołączono do wyzwania! Powodzenia!', 'success');
                    // Odśwież cały widok, aby zaktualizować obie listy wyzwań
                    render.view('social');
                } catch (error) {
                    joinBtn.disabled = false;
                    joinBtn.textContent = 'Dołącz';
                }
                return;
            }
        });
    }

    function addAnalysisEventListeners() {
        selectors.generateAnalysisBtn.addEventListener('click', handle.generateAnalysis);

        selectors.analysisStartDate.addEventListener('change', () => handle.setAnalysisDateRange(null));
        selectors.analysisEndDate.addEventListener('change', () => handle.setAnalysisDateRange(null));

        $$('.timeframe-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                $$('.timeframe-btn').forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                handle.setAnalysisDateRange(parseInt(e.target.dataset.range));
            });
        });
    }

    function makeListsSortable() {
        $$('.sortable-list').forEach(list => {
            // Sprawdź, czy Sortable już nie jest zainicjalizowany na tej liście
            if (list.sortable) {
                list.sortable.destroy(); // Zniszcz poprzednią instancję, jeśli istnieje
            }
            list.sortable = new Sortable(list, { // Przypisz instancję do elementu DOM
                animation: 150, 
                handle: '.drag-handle', 
                ghostClass: 'sortable-ghost' 
            });
        });
    }

    function updateMacroCalculations() {
        const calories = parseInt($('#profile-calories')?.value) || 0;
        const sliders = $$('.macro-slider');
        const outputs = $$('.macro-slider + output');
        const grams = { p: $('#profile-protein-g'), f: $('#profile-fat-g'), c: $('#profile-carbs-g') };

        // Upewnij się, że suma procentów wynosi 100
        let totalPerc = 0;
        sliders.forEach(slider => totalPerc += parseInt(slider.value));

        if (totalPerc !== 100) {
            // Prosta korekta: rozdziel różnicę proporcjonalnie lub na ostatni slider
            // Na razie dodajmy do ostatniego, aby suma zawsze wynosiła 100
            if (sliders.length > 0) {
                sliders[sliders.length - 1].value = parseInt(sliders[sliders.length - 1].value) + (100 - totalPerc);
            }
        }

        sliders.forEach((slider, index) => { outputs[index].textContent = `${slider.value}%`; });

        const p_perc = parseInt(sliders[0].value);
        const f_perc = parseInt(sliders[1].value);
        const c_perc = parseInt(sliders[2].value);

        grams.p.value = Math.round((calories * p_perc / 100) / 4);
        grams.f.value = Math.round((calories * f_perc / 100) / 9);
        grams.c.value = Math.round((calories * c_perc / 100) / 4);
    }

    // === INICJALIZACJA APLIKACJI ===
    const initApp = async () => {
        // Obsługa tokenu z Google OAuth w URL
        const urlParams = new URLSearchParams(window.location.search);
        const tokenFromUrl = urlParams.get('token');
        if (tokenFromUrl) {
            localStorage.setItem('token', tokenFromUrl);
            // Wyczyść URL, aby token nie był widoczny
            window.history.replaceState({}, document.title, "/");
        }

        addMainAppEventListeners();

        const savedTheme = localStorage.getItem('theme') || 'system';
        handle.themeChange(savedTheme, false);

        const token = localStorage.getItem('token');
        if (token) {
            state.token = token;
            try {
                // Pobierz dane zalogowanego użytkownika
                state.currentUser = await api.getMe();
                render.app();
            } catch (error) {
                console.error("Błąd inicjalizacji sesji, token mógł wygasnąć.", error);
                handle.logout(); // Wyloguj, jeśli token jest nieważny
            }
        } else {
            render.app(); // Pokaż ekran logowania, jeśli nie ma tokenu
        }
    };

    initApp();
});
