document.addEventListener('DOMContentLoaded', function() {
    // Загружаем конфигурацию при загрузке страницы
    fetchConfig();
    
    // Обработчик для кнопки сохранения
    document.getElementById('saveButton').addEventListener('click', saveConfig);
    
    // Обработчики для пунктов меню
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.addEventListener('click', function() {
            // Убираем активный класс у всех пунктов
            document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
            // Добавляем активный класс текущему пункту
            this.classList.add('active');
            
            // Показываем соответствующую секцию
            const section = this.dataset.section;
            document.querySelectorAll('.config-section').forEach(s => s.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');
        });
    });
});

// Функция для форматирования названий полей
function formatFieldName(name) {
    // Заменяем подчеркивания на пробелы
    let formatted = name.replace(/_/g, ' ');
    
    // Делаем первую букву заглавной, остальные строчными
    return formatted.charAt(0).toUpperCase() + formatted.slice(1).toLowerCase();
}

// Функция для загрузки конфигурации с сервера
async function fetchConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        renderConfig(config);
    } catch (error) {
        showNotification('Failed to load configuration: ' + error.message, 'error');
    }
}

// Функция для сохранения конфигурации
async function saveConfig() {
    try {
        const config = collectFormData();
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('Configuration saved successfully!', 'success');
        } else {
            showNotification('Error: ' + result.message, 'error');
        }
    } catch (error) {
        showNotification('Failed to save configuration: ' + error.message, 'error');
    }
}

// Функция для сбора данных формы
function collectFormData() {
    config = {}
    
    // Собираем данные из всех полей ввода
    document.querySelectorAll('[data-config-path]').forEach(element => {
        const path = element.dataset.configPath.split('.');
        let current = config;
        
        // Check if this is a withdrawal field (has pattern like EXCHANGES.withdrawals[0].field)
        const isWithdrawalField = path.length >= 2 && path[1].includes('withdrawals[');
        
        // For regular fields
        if (!isWithdrawalField) {
            // Создаем вложенные объекты по пути
            for (let i = 0; i < path.length - 1; i++) {
                if (!current[path[i]]) {
                    current[path[i]] = {};
                }
                current = current[path[i]];
            }
        } 
        // For withdrawal fields
        else {
            // Ensure EXCHANGES exists
            if (!current['EXCHANGES']) {
                current['EXCHANGES'] = {};
            }
            
            // Ensure withdrawals array exists
            if (!current['EXCHANGES']['withdrawals']) {
                current['EXCHANGES']['withdrawals'] = [{}];
            }
            
            // Extract the index from the pattern withdrawals[X]
            const withdrawalIndexMatch = path[1].match(/withdrawals\[(\d+)\]/);
            const withdrawalIndex = withdrawalIndexMatch ? parseInt(withdrawalIndexMatch[1]) : 0;
            
            // Ensure the particular withdrawal object exists
            if (!current['EXCHANGES']['withdrawals'][withdrawalIndex]) {
                current['EXCHANGES']['withdrawals'][withdrawalIndex] = {};
            }
            
            current = current['EXCHANGES']['withdrawals'][withdrawalIndex];
            // Last part of the path for withdrawals is the actual field
            path[1] = path[path.length - 1]; 
            path.length = 2;
        }
        
        const lastKey = path[path.length - 1];
        
        if (element.type === 'checkbox') {
            current[lastKey] = element.checked;
        } else if (element.classList.contains('tags-input')) {
            // Обработка полей с тегами
            const tags = Array.from(element.querySelectorAll('.tag-text'))
                .map(tag => tag.textContent.trim());
            current[lastKey] = tags;
        } else if (element.classList.contains('range-min')) {
            const rangeKey = lastKey.replace('_MIN', '');
            if (!current[rangeKey]) {
                current[rangeKey] = [0, 0];
            }
            current[rangeKey][0] = parseInt(element.value, 10);

            // Check if this is a float type field
            if (element.dataset.type === 'float') {
                current[rangeKey][0] = parseFloat(element.value);
            } else {
                current[rangeKey][0] = parseInt(element.value, 10);
            }
        } else if (element.classList.contains('range-max')) {
            const rangeKey = lastKey.replace('_MAX', '');
            if (!current[rangeKey]) {
                current[rangeKey] = [0, 0];
            }
            current[rangeKey][1] = parseInt(element.value, 10);

            // Check if this is a float type field
            if (element.dataset.type === 'float') {
                current[rangeKey][1] = parseFloat(element.value);
            } else {
                current[rangeKey][1] = parseInt(element.value, 10);
            }
        } else if (element.classList.contains('list-input')) {
            // Для списков (разделенных запятыми)
            const items = element.value.split(',')
                .map(item => item.trim())
                .filter(item => item !== '');
                
            // Преобразуем в числа, если это числовой список
            if (element.dataset.type === 'number-list') {
                current[lastKey] = items.map(item => parseInt(item, 10));
            } else {
                current[lastKey] = items;
            }
        } else {
            // Для обычных полей
            if (element.dataset.type === 'number') {
                current[lastKey] = parseInt(element.value, 10);
            } else if (element.dataset.type === 'float') {
                current[lastKey] = parseFloat(element.value);
            } else {
                current[lastKey] = element.value;
            }
        }
    });
    
    return config;
}

// Функция для отображения конфигурации
function renderConfig(config) {
    const container = document.getElementById('configContainer');
    container.innerHTML = ''; // Очищаем контейнер
    
    // Создаем секции для каждой категории
    const sections = {
        'settings': { key: 'SETTINGS', title: 'Settings', icon: 'cog' },
        'flow': { key: 'FLOW', title: 'Flow', icon: 'exchange-alt' },
        'faucet': { key: 'FAUCET', title: 'Faucet and Captcha', icon: 'robot' },
        'rpcs': { key: 'RPCS', title: 'RPCs', icon: 'network-wired' },
        'others': { key: 'OTHERS', title: 'Others', icon: 'ellipsis-h' },
        'swaps': { key: 'SWAPS', title: 'Swaps', icon: 'sync-alt' },
        'stakings': { key: 'STAKINGS', title: 'Stakings', icon: 'coins' },
        'mints': { key: 'MINTS', title: 'Mints', icon: 'hammer' },
        'crustyswap': { key: 'CRUSTY_SWAP', title: 'Crusty Swap', icon: 'network-wired' },
        'exchanges': { key: 'EXCHANGES', title: 'Exchanges', icon: 'exchange-alt' }
    };
    
    // Создаем все секции
    Object.entries(sections).forEach(([sectionId, { key, title, icon }], index) => {
        const section = document.createElement('div');
        section.id = `${sectionId}-section`;
        section.className = `config-section ${index === 0 ? 'active' : ''}`;
        
        const sectionTitle = document.createElement('h2');
        sectionTitle.className = 'section-title';
        sectionTitle.innerHTML = `<i class="fas fa-${icon}"></i> ${title}`;
        section.appendChild(sectionTitle);
        
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'config-cards';
        section.appendChild(cardsContainer);
        
        // Заполняем секцию данными
        if (config[key]) {
            if (key === 'SETTINGS') {
                // Карточка для основных настроек
                createCard(cardsContainer, 'Basic Settings', 'sliders-h', [
                    { key: 'THREADS', value: config[key]['THREADS'] },
                    { key: 'ATTEMPTS', value: config[key]['ATTEMPTS'] },
                    { key: 'SHUFFLE_WALLETS', value: config[key]['SHUFFLE_WALLETS'] },
                    { key: 'WAIT_FOR_TRANSACTION_CONFIRMATION_IN_SECONDS', value: config[key]['WAIT_FOR_TRANSACTION_CONFIRMATION_IN_SECONDS'] }
                ], key);
                
                // Карточка для диапазонов аккаунтов
                createCard(cardsContainer, 'Account Settings', 'users', [
                    { key: 'ACCOUNTS_RANGE', value: config[key]['ACCOUNTS_RANGE'] },
                    { key: 'EXACT_ACCOUNTS_TO_USE', value: config[key]['EXACT_ACCOUNTS_TO_USE'], isSpaceList: true }
                ], key);
                
                // Карточка для пауз
                createCard(cardsContainer, 'Timing Settings', 'clock', [
                    { key: 'PAUSE_BETWEEN_ATTEMPTS', value: config[key]['PAUSE_BETWEEN_ATTEMPTS'] },
                    { key: 'PAUSE_BETWEEN_SWAPS', value: config[key]['PAUSE_BETWEEN_SWAPS'] },
                    { key: 'RANDOM_PAUSE_BETWEEN_ACCOUNTS', value: config[key]['RANDOM_PAUSE_BETWEEN_ACCOUNTS'] },
                    { key: 'RANDOM_PAUSE_BETWEEN_ACTIONS', value: config[key]['RANDOM_PAUSE_BETWEEN_ACTIONS'] },
                    { key: 'RANDOM_INITIALIZATION_PAUSE', value: config[key]['RANDOM_INITIALIZATION_PAUSE'] }
                ], key);
                
                // Карточка для Telegram
                createCard(cardsContainer, 'Telegram Settings', 'paper-plane', [
                    { key: 'SEND_TELEGRAM_LOGS', value: config[key]['SEND_TELEGRAM_LOGS'] },
                    { key: 'TELEGRAM_BOT_TOKEN', value: config[key]['TELEGRAM_BOT_TOKEN'] },
                    { key: 'TELEGRAM_USERS_IDS', value: config[key]['TELEGRAM_USERS_IDS'], isSpaceList: true }
                ], key);
            } else if (key === 'FLOW') {
                createCard(cardsContainer, 'Flow Settings', 'exchange-alt', [
                    { key: 'SKIP_FAILED_TASKS', value: config[key]['SKIP_FAILED_TASKS'] }
                ], key);
            } else if (key === 'FAUCET') {
                // Карточка для настроек Faucet
                createCard(cardsContainer, 'Captcha Solvers', 'puzzle-piece', [
                    { key: 'SOLVIUM_API_KEY', value: config[key]['SOLVIUM_API_KEY'] },
                    { key: 'USE_CAPSOLVER', value: config[key]['USE_CAPSOLVER'] },
                    { key: 'CAPSOLVER_API_KEY', value: config[key]['CAPSOLVER_API_KEY'] }
                ], key);
            } else if (key === 'RPCS') {
                // Специальная обработка для RPCs
                createCard(cardsContainer, 'RPC Settings', 'network-wired', 
                    Object.entries(config[key]).map(([k, v]) => ({ 
                        key: k, 
                        value: v, 
                        isList: true,
                        isArray: true  // Добавляем флаг для массивов
                    })), 
                    key
                );
            } else if (key === 'OTHERS') {
                // Остальные категории
                createCard(cardsContainer, `Other Settings`, icon, [
                    { key: 'SKIP_SSL_VERIFICATION', value: config[key]['SKIP_SSL_VERIFICATION'] },
                    { key: 'USE_PROXY_FOR_RPC', value: config[key]['USE_PROXY_FOR_RPC'] }
                ], key);
            } else if (key === 'SWAPS') {
                // BEBOP
                if (config[key]['BEBOP']) {
                    createCard(cardsContainer, 'Bebop Swap Settings', 'exchange', 
                        Object.entries(config[key]['BEBOP']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isRange: Array.isArray(v) && v.length === 2 && typeof v[0] === 'number',
                            isBoolean: typeof v === 'boolean'
                        })), 
                        `${key}.BEBOP`
                    );
                }
                
                // GTE
                if (config[key]['GTE']) {
                    createCard(cardsContainer, 'GTE Swap Settings', 'sync', 
                        Object.entries(config[key]['GTE']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isRange: Array.isArray(v) && v.length === 2 && typeof v[0] === 'number',
                            isBoolean: typeof v === 'boolean'
                        })), 
                        `${key}.GTE`
                    );
                }
            } else if (key === 'STAKINGS') {
                // TEKO_FINANCE
                if (config[key]['TEKO_FINANCE']) {
                    createCard(cardsContainer, 'Teko Finance Settings', 'chart-line', 
                        Object.entries(config[key]['TEKO_FINANCE']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isRange: Array.isArray(v) && v.length === 2 && typeof v[0] === 'number',
                            isNumber: typeof v === 'number' && !Array.isArray(v),
                            isBoolean: typeof v === 'boolean'
                        })), 
                        `${key}.TEKO_FINANCE`
                    );
                }
            } else if (key === 'MINTS') {
                // XL_MEME
                if (config[key]['XL_MEME']) {
                    createCard(cardsContainer, 'XL Meme Settings', 'fire', 
                        Object.entries(config[key]['XL_MEME']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isRange: Array.isArray(v) && v.length === 2,
                            isList: Array.isArray(v) && k === 'CONTRACTS_TO_BUY'
                        })), 
                        `${key}.XL_MEME`
                    );
                }

                // RARIBLE
                if (config[key]['RARIBLE']) {
                    createCard(cardsContainer, 'Rarible Settings', 'palette', 
                        Object.entries(config[key]['RARIBLE']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isList: Array.isArray(v) && k === 'CONTRACTS_TO_BUY'
                        })), 
                        `${key}.RARIBLE`
                    );
                }

                // OMNIHUB
                if (config[key]['OMNIHUB']) {
                    createCard(cardsContainer, 'OmniHub Settings', 'cube', 
                        Object.entries(config[key]['OMNIHUB']).map(([k, v]) => ({ 
                            key: k, 
                            value: v, 
                            isNumber: typeof v === 'number' && !Array.isArray(v)
                        })), 
                        `${key}.OMNIHUB`
                    );
                }
            } else if (key === 'CRUSTY_SWAP') {
                // CRUSTY_SWAP with more horizontal layout
                const cardDiv = document.createElement('div');
                cardDiv.className = 'config-card';
                
                const titleDiv = document.createElement('div');
                titleDiv.className = 'card-title';
                
                const icon = document.createElement('i');
                icon.className = 'fas fa-network-wired';
                titleDiv.appendChild(icon);
                
                const titleText = document.createElement('span');
                titleText.textContent = 'Crusty Swap Settings';
                titleDiv.appendChild(titleText);
                
                cardDiv.appendChild(titleDiv);
                
                // Networks to refuel from
                const networksFieldDiv = document.createElement('div');
                networksFieldDiv.className = 'config-field';
                
                const networksLabel = document.createElement('label');
                networksLabel.className = 'field-label';
                networksLabel.textContent = 'Networks to refuel from';
                networksFieldDiv.appendChild(networksLabel);
                
                const networksContainer = document.createElement('div');
                networksContainer.className = 'tags-input';
                networksContainer.dataset.configPath = `${key}.NETWORKS_TO_REFUEL_FROM`;
                
                // Predefined network options
                const availableNetworks = ['Arbitrum', 'Optimism', 'Base'];
                
                // Add existing networks as tags
                if (config[key].NETWORKS_TO_REFUEL_FROM && Array.isArray(config[key].NETWORKS_TO_REFUEL_FROM)) {
                    config[key].NETWORKS_TO_REFUEL_FROM.forEach(network => {
                        if (availableNetworks.includes(network)) {
                            const tag = document.createElement('div');
                            tag.className = 'tag';
                            
                            const tagText = document.createElement('span');
                            tagText.className = 'tag-text';
                            tagText.textContent = network;
                            
                            const removeBtn = document.createElement('button');
                            removeBtn.className = 'tag-remove';
                            removeBtn.innerHTML = '&times;';
                            removeBtn.addEventListener('click', function() {
                                tag.remove();
                            });
                            
                            tag.appendChild(tagText);
                            tag.appendChild(removeBtn);
                            networksContainer.appendChild(tag);
                        }
                    });
                }
                
                // Add dropdown for new networks
                const networksSelect = document.createElement('select');
                networksSelect.className = 'networks-select';
                networksSelect.style.background = 'transparent';
                networksSelect.style.border = 'none';
                networksSelect.style.color = 'var(--text-primary)';
                networksSelect.style.padding = '5px';
                
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Add network...';
                defaultOption.selected = true;
                defaultOption.disabled = true;
                networksSelect.appendChild(defaultOption);
                
                availableNetworks.forEach(network => {
                    const option = document.createElement('option');
                    option.value = network;
                    option.textContent = network;
                    option.style.color = '#000';
                    option.style.background = '#fff';
                    networksSelect.appendChild(option);
                });
                
                networksSelect.addEventListener('change', function() {
                    if (this.value) {
                        // Check if network already exists
                        const tags = networksContainer.querySelectorAll('.tag-text');
                        let exists = false;
                        tags.forEach(tag => {
                            if (tag.textContent === this.value) {
                                exists = true;
                            }
                        });
                        
                        if (!exists) {
                            const tag = document.createElement('div');
                            tag.className = 'tag';
                            
                            const tagText = document.createElement('span');
                            tagText.className = 'tag-text';
                            tagText.textContent = this.value;
                            
                            const removeBtn = document.createElement('button');
                            removeBtn.className = 'tag-remove';
                            removeBtn.innerHTML = '&times;';
                            removeBtn.addEventListener('click', function() {
                                tag.remove();
                            });
                            
                            tag.appendChild(tagText);
                            tag.appendChild(removeBtn);
                            networksContainer.insertBefore(tag, this);
                        }
                        
                        // Reset select
                        this.value = '';
                    }
                });
                
                networksContainer.appendChild(networksSelect);
                networksFieldDiv.appendChild(networksContainer);
                cardDiv.appendChild(networksFieldDiv);
                
                // Amount to refuel - side by side min and max
                const amountFieldsDiv = document.createElement('div');
                amountFieldsDiv.className = 'config-field horizontal-fields';
                amountFieldsDiv.style.display = 'flex';
                amountFieldsDiv.style.gap = '15px';
                
                // Min amount field
                const minAmountDiv = document.createElement('div');
                minAmountDiv.style.flex = '1';
                
                const minAmountLabel = document.createElement('label');
                minAmountLabel.className = 'field-label';
                minAmountLabel.textContent = 'Amount (min)';
                minAmountDiv.appendChild(minAmountLabel);
                
                const minAmountInput = document.createElement('input');
                minAmountInput.type = 'number';
                minAmountInput.step = '0.0001';
                minAmountInput.className = 'field-input range-min';
                minAmountInput.value = config[key].AMOUNT_TO_REFUEL[0] || 0.0001;
                minAmountInput.dataset.configPath = `${key}.AMOUNT_TO_REFUEL_MIN`;
                minAmountInput.dataset.type = 'float';
                
                minAmountDiv.appendChild(minAmountInput);
                amountFieldsDiv.appendChild(minAmountDiv);
                
                // Max amount field
                const maxAmountDiv = document.createElement('div');
                maxAmountDiv.style.flex = '1';
                
                const maxAmountLabel = document.createElement('label');
                maxAmountLabel.className = 'field-label';
                maxAmountLabel.textContent = 'Amount (max)';
                maxAmountDiv.appendChild(maxAmountLabel);
                
                const maxAmountInput = document.createElement('input');
                maxAmountInput.type = 'number';
                maxAmountInput.step = '0.0001';
                maxAmountInput.className = 'field-input range-max';
                maxAmountInput.value = config[key].AMOUNT_TO_REFUEL[1] || 0.00015;
                maxAmountInput.dataset.configPath = `${key}.AMOUNT_TO_REFUEL_MAX`;
                maxAmountInput.dataset.type = 'float';
                
                maxAmountDiv.appendChild(maxAmountInput);
                amountFieldsDiv.appendChild(maxAmountDiv);
                
                cardDiv.appendChild(amountFieldsDiv);
                
                // 2-column layout for remaining options
                const optionsContainer = document.createElement('div');
                optionsContainer.style.display = 'flex';
                optionsContainer.style.flexWrap = 'wrap';
                optionsContainer.style.gap = '15px';
                
                // Minimum balance to refuel
                const minBalanceDiv = document.createElement('div');
                minBalanceDiv.className = 'config-field';
                minBalanceDiv.style.flex = '1';
                minBalanceDiv.style.minWidth = '200px';
                
                const minBalanceLabel = document.createElement('label');
                minBalanceLabel.className = 'field-label';
                minBalanceLabel.textContent = 'Minimum balance to refuel';
                minBalanceDiv.appendChild(minBalanceLabel);
                
                const minBalanceInput = document.createElement('input');
                minBalanceInput.type = 'number';
                minBalanceInput.step = '0.0001';
                minBalanceInput.className = 'field-input';
                minBalanceInput.value = config[key].MINIMUM_BALANCE_TO_REFUEL || 0;
                minBalanceInput.dataset.configPath = `${key}.MINIMUM_BALANCE_TO_REFUEL`;
                minBalanceInput.dataset.type = 'float';
                
                minBalanceDiv.appendChild(minBalanceInput);
                optionsContainer.appendChild(minBalanceDiv);
                
                // Bridge all max amount
                const bridgeMaxAmountDiv = document.createElement('div');
                bridgeMaxAmountDiv.className = 'config-field';
                bridgeMaxAmountDiv.style.flex = '1';
                bridgeMaxAmountDiv.style.minWidth = '200px';
                
                const bridgeMaxAmountLabel = document.createElement('label');
                bridgeMaxAmountLabel.className = 'field-label';
                bridgeMaxAmountLabel.textContent = 'Bridge all max amount';
                bridgeMaxAmountDiv.appendChild(bridgeMaxAmountLabel);
                
                const bridgeMaxAmountInput = document.createElement('input');
                bridgeMaxAmountInput.type = 'number';
                bridgeMaxAmountInput.step = '0.0001';
                bridgeMaxAmountInput.className = 'field-input';
                bridgeMaxAmountInput.value = config[key].BRIDGE_ALL_MAX_AMOUNT || 0.01;
                bridgeMaxAmountInput.dataset.configPath = `${key}.BRIDGE_ALL_MAX_AMOUNT`;
                bridgeMaxAmountInput.dataset.type = 'float';
                
                bridgeMaxAmountDiv.appendChild(bridgeMaxAmountInput);
                optionsContainer.appendChild(bridgeMaxAmountDiv);
                
                // Max wait time
                const maxWaitTimeDiv = document.createElement('div');
                maxWaitTimeDiv.className = 'config-field';
                maxWaitTimeDiv.style.flex = '1';
                maxWaitTimeDiv.style.minWidth = '200px';
                
                const maxWaitTimeLabel = document.createElement('label');
                maxWaitTimeLabel.className = 'field-label';
                maxWaitTimeLabel.textContent = 'Max wait time';
                maxWaitTimeDiv.appendChild(maxWaitTimeLabel);
                
                const maxWaitTimeInput = document.createElement('input');
                maxWaitTimeInput.type = 'number';
                maxWaitTimeInput.className = 'field-input';
                maxWaitTimeInput.value = config[key].MAX_WAIT_TIME || 99999;
                maxWaitTimeInput.dataset.configPath = `${key}.MAX_WAIT_TIME`;
                maxWaitTimeInput.dataset.type = 'number';
                
                maxWaitTimeDiv.appendChild(maxWaitTimeInput);
                optionsContainer.appendChild(maxWaitTimeDiv);
                
                // Create checkboxes in 2-column layout
                const checkboxesContainer = document.createElement('div');
                checkboxesContainer.style.display = 'flex';
                checkboxesContainer.style.gap = '20px';
                checkboxesContainer.style.marginTop = '10px';
                
                // Wait for funds checkbox
                const waitFundsDiv = document.createElement('div');
                waitFundsDiv.className = 'checkbox-field';
                waitFundsDiv.style.flex = '1';
                
                const waitFundsInput = document.createElement('input');
                waitFundsInput.type = 'checkbox';
                waitFundsInput.className = 'checkbox-input';
                waitFundsInput.checked = config[key].WAIT_FOR_FUNDS_TO_ARRIVE || false;
                waitFundsInput.dataset.configPath = `${key}.WAIT_FOR_FUNDS_TO_ARRIVE`;
                waitFundsInput.id = `checkbox-wait-funds-crusty`;
                
                const waitFundsLabel = document.createElement('label');
                waitFundsLabel.className = 'checkbox-label';
                waitFundsLabel.textContent = 'Wait for funds to arrive';
                waitFundsLabel.htmlFor = waitFundsInput.id;
                
                waitFundsDiv.appendChild(waitFundsInput);
                waitFundsDiv.appendChild(waitFundsLabel);
                checkboxesContainer.appendChild(waitFundsDiv);
                
                // Bridge all checkbox
                const bridgeAllDiv = document.createElement('div');
                bridgeAllDiv.className = 'checkbox-field';
                bridgeAllDiv.style.flex = '1';
                
                const bridgeAllInput = document.createElement('input');
                bridgeAllInput.type = 'checkbox';
                bridgeAllInput.className = 'checkbox-input';
                bridgeAllInput.checked = config[key].BRIDGE_ALL || false;
                bridgeAllInput.dataset.configPath = `${key}.BRIDGE_ALL`;
                bridgeAllInput.id = `checkbox-bridge-all`;
                
                const bridgeAllLabel = document.createElement('label');
                bridgeAllLabel.className = 'checkbox-label';
                bridgeAllLabel.textContent = 'Bridge all';
                bridgeAllLabel.htmlFor = bridgeAllInput.id;
                
                bridgeAllDiv.appendChild(bridgeAllInput);
                bridgeAllDiv.appendChild(bridgeAllLabel);
                checkboxesContainer.appendChild(bridgeAllDiv);
                
                optionsContainer.appendChild(checkboxesContainer);
                cardDiv.appendChild(optionsContainer);
                
                cardsContainer.appendChild(cardDiv);
            } else if (key === 'EXCHANGES') {
                // Basic exchange settings (exclude withdrawals)
                const exchangeCardDiv = document.createElement('div');
                exchangeCardDiv.className = 'config-card';
                
                const exchangeTitleDiv = document.createElement('div');
                exchangeTitleDiv.className = 'card-title';
                
                const exchangeIcon = document.createElement('i');
                exchangeIcon.className = 'fas fa-exchange-alt';
                exchangeTitleDiv.appendChild(exchangeIcon);
                
                const exchangeTitleText = document.createElement('span');
                exchangeTitleText.textContent = 'Exchange Settings';
                exchangeTitleDiv.appendChild(exchangeTitleText);
                
                exchangeCardDiv.appendChild(exchangeTitleDiv);
                
                // Exchange name - dropdown instead of text input
                const nameFieldDiv = document.createElement('div');
                nameFieldDiv.className = 'config-field';
                
                const nameLabel = document.createElement('label');
                nameLabel.className = 'field-label';
                nameLabel.textContent = 'Name';
                nameFieldDiv.appendChild(nameLabel);
                
                const nameSelect = document.createElement('select');
                nameSelect.className = 'field-input';
                nameSelect.dataset.configPath = `${key}.name`;
                
                const options = ['OKX', 'BITGET'];
                options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = opt;
                    if (config[key].name === opt) {
                        option.selected = true;
                    }
                    nameSelect.appendChild(option);
                });
                
                nameFieldDiv.appendChild(nameSelect);
                exchangeCardDiv.appendChild(nameFieldDiv);
                
                // API Key field
                const apiKeyFieldDiv = document.createElement('div');
                apiKeyFieldDiv.className = 'config-field';
                
                const apiKeyLabel = document.createElement('label');
                apiKeyLabel.className = 'field-label';
                apiKeyLabel.textContent = 'API Key';
                apiKeyFieldDiv.appendChild(apiKeyLabel);
                
                const apiKeyInput = document.createElement('input');
                apiKeyInput.type = 'text';
                apiKeyInput.className = 'field-input';
                apiKeyInput.value = config[key].apiKey || '';
                apiKeyInput.dataset.configPath = `${key}.apiKey`;
                
                apiKeyFieldDiv.appendChild(apiKeyInput);
                exchangeCardDiv.appendChild(apiKeyFieldDiv);
                
                // Secret Key field
                const secretKeyFieldDiv = document.createElement('div');
                secretKeyFieldDiv.className = 'config-field';
                
                const secretKeyLabel = document.createElement('label');
                secretKeyLabel.className = 'field-label';
                secretKeyLabel.textContent = 'Secret Key';
                secretKeyFieldDiv.appendChild(secretKeyLabel);
                
                const secretKeyInput = document.createElement('input');
                secretKeyInput.type = 'text';
                secretKeyInput.className = 'field-input';
                secretKeyInput.value = config[key].secretKey || '';
                secretKeyInput.dataset.configPath = `${key}.secretKey`;
                
                secretKeyFieldDiv.appendChild(secretKeyInput);
                exchangeCardDiv.appendChild(secretKeyFieldDiv);
                
                // Passphrase field
                const passphraseFieldDiv = document.createElement('div');
                passphraseFieldDiv.className = 'config-field';
                
                const passphraseLabel = document.createElement('label');
                passphraseLabel.className = 'field-label';
                passphraseLabel.textContent = 'Passphrase';
                passphraseFieldDiv.appendChild(passphraseLabel);
                
                const passphraseInput = document.createElement('input');
                passphraseInput.type = 'text';
                passphraseInput.className = 'field-input';
                passphraseInput.value = config[key].passphrase || '';
                passphraseInput.dataset.configPath = `${key}.passphrase`;
                
                passphraseFieldDiv.appendChild(passphraseInput);
                exchangeCardDiv.appendChild(passphraseFieldDiv);
                
                cardsContainer.appendChild(exchangeCardDiv);
                
                // Create withdrawal settings card with more horizontal layout
                if (config[key].withdrawals && config[key].withdrawals.length > 0) {
                    const withdrawalConfig = config[key].withdrawals[0];
                    
                    const withdrawalCardDiv = document.createElement('div');
                    withdrawalCardDiv.className = 'config-card';
                    
                    const withdrawalTitleDiv = document.createElement('div');
                    withdrawalTitleDiv.className = 'card-title';
                    
                    const withdrawalIcon = document.createElement('i');
                    withdrawalIcon.className = 'fas fa-money-bill-transfer';
                    withdrawalTitleDiv.appendChild(withdrawalIcon);
                    
                    const withdrawalTitleText = document.createElement('span');
                    withdrawalTitleText.textContent = 'Withdrawal Settings';
                    withdrawalTitleDiv.appendChild(withdrawalTitleText);
                    
                    withdrawalCardDiv.appendChild(withdrawalTitleDiv);
                    
                    // Currency field - hardcoded to ETH
                    const currencyFieldDiv = document.createElement('div');
                    currencyFieldDiv.className = 'config-field';
                    
                    const currencyLabel = document.createElement('label');
                    currencyLabel.className = 'field-label';
                    currencyLabel.textContent = 'Currency';
                    currencyFieldDiv.appendChild(currencyLabel);
                    
                    const currencyInput = document.createElement('input');
                    currencyInput.type = 'text';
                    currencyInput.className = 'field-input';
                    currencyInput.value = 'ETH';
                    currencyInput.readOnly = true;
                    currencyInput.disabled = true;
                    currencyInput.dataset.configPath = `${key}.withdrawals[0].currency`;
                    
                    currencyFieldDiv.appendChild(currencyInput);
                    withdrawalCardDiv.appendChild(currencyFieldDiv);
                    
                    // Networks field - multi-select with predefined options
                    const networksFieldDiv = document.createElement('div');
                    networksFieldDiv.className = 'config-field';
                    
                    const networksLabel = document.createElement('label');
                    networksLabel.className = 'field-label';
                    networksLabel.textContent = 'Networks';
                    networksFieldDiv.appendChild(networksLabel);
                    
                    const networksContainer = document.createElement('div');
                    networksContainer.className = 'tags-input';
                    networksContainer.dataset.configPath = `${key}.withdrawals[0].networks`;
                    
                    // Predefined network options
                    const availableNetworks = ['Arbitrum', 'Optimism', 'Base'];
                    
                    // Add existing networks as tags
                    if (withdrawalConfig.networks && Array.isArray(withdrawalConfig.networks)) {
                        withdrawalConfig.networks.forEach(network => {
                            if (availableNetworks.includes(network)) {
                                const tag = document.createElement('div');
                                tag.className = 'tag';
                                
                                const tagText = document.createElement('span');
                                tagText.className = 'tag-text';
                                tagText.textContent = network;
                                
                                const removeBtn = document.createElement('button');
                                removeBtn.className = 'tag-remove';
                                removeBtn.innerHTML = '&times;';
                                removeBtn.addEventListener('click', function() {
                                    tag.remove();
                                });
                                
                                tag.appendChild(tagText);
                                tag.appendChild(removeBtn);
                                networksContainer.appendChild(tag);
                            }
                        });
                    }
                    
                    // Add dropdown for new networks
                    const networksSelect = document.createElement('select');
                    networksSelect.className = 'networks-select';
                    networksSelect.style.background = 'transparent';
                    networksSelect.style.border = 'none';
                    networksSelect.style.color = 'var(--text-primary)';
                    networksSelect.style.padding = '5px';
                    
                    const defaultOption = document.createElement('option');
                    defaultOption.value = '';
                    defaultOption.textContent = 'Add network...';
                    defaultOption.selected = true;
                    defaultOption.disabled = true;
                    networksSelect.appendChild(defaultOption);
                    
                    availableNetworks.forEach(network => {
                        const option = document.createElement('option');
                        option.value = network;
                        option.textContent = network;
                        option.style.color = '#000';
                        option.style.background = '#fff';
                        networksSelect.appendChild(option);
                    });
                    
                    networksSelect.addEventListener('change', function() {
                        if (this.value) {
                            // Check if network already exists
                            const tags = networksContainer.querySelectorAll('.tag-text');
                            let exists = false;
                            tags.forEach(tag => {
                                if (tag.textContent === this.value) {
                                    exists = true;
                                }
                            });
                            
                            if (!exists) {
                                const tag = document.createElement('div');
                                tag.className = 'tag';
                                
                                const tagText = document.createElement('span');
                                tagText.className = 'tag-text';
                                tagText.textContent = this.value;
                                
                                const removeBtn = document.createElement('button');
                                removeBtn.className = 'tag-remove';
                                removeBtn.innerHTML = '&times;';
                                removeBtn.addEventListener('click', function() {
                                    tag.remove();
                                });
                                
                                tag.appendChild(tagText);
                                tag.appendChild(removeBtn);
                                networksContainer.insertBefore(tag, this);
                            }
                            
                            // Reset select
                            this.value = '';
                        }
                    });
                    
                    networksContainer.appendChild(networksSelect);
                    networksFieldDiv.appendChild(networksContainer);
                    withdrawalCardDiv.appendChild(networksFieldDiv);
                    
                    // Min and Max amount fields side by side
                    const amountFieldsDiv = document.createElement('div');
                    amountFieldsDiv.className = 'config-field horizontal-fields';
                    amountFieldsDiv.style.display = 'flex';
                    amountFieldsDiv.style.gap = '15px';
                    
                    // Min amount field
                    const minAmountDiv = document.createElement('div');
                    minAmountDiv.style.flex = '1';
                    
                    const minAmountLabel = document.createElement('label');
                    minAmountLabel.className = 'field-label';
                    minAmountLabel.textContent = 'Min amount';
                    minAmountDiv.appendChild(minAmountLabel);
                    
                    const minAmountInput = document.createElement('input');
                    minAmountInput.type = 'number';
                    minAmountInput.step = '0.0001';
                    minAmountInput.className = 'field-input';
                    minAmountInput.value = withdrawalConfig.min_amount || 0.0003;
                    minAmountInput.dataset.configPath = `${key}.withdrawals[0].min_amount`;
                    minAmountInput.dataset.type = 'float';
                    
                    minAmountDiv.appendChild(minAmountInput);
                    amountFieldsDiv.appendChild(minAmountDiv);
                    
                    // Max amount field
                    const maxAmountDiv = document.createElement('div');
                    maxAmountDiv.style.flex = '1';
                    
                    const maxAmountLabel = document.createElement('label');
                    maxAmountLabel.className = 'field-label';
                    maxAmountLabel.textContent = 'Max amount';
                    maxAmountDiv.appendChild(maxAmountLabel);
                    
                    const maxAmountInput = document.createElement('input');
                    maxAmountInput.type = 'number';
                    maxAmountInput.step = '0.0001';
                    maxAmountInput.className = 'field-input';
                    maxAmountInput.value = withdrawalConfig.max_amount || 0.0004;
                    maxAmountInput.dataset.configPath = `${key}.withdrawals[0].max_amount`;
                    maxAmountInput.dataset.type = 'float';
                    
                    maxAmountDiv.appendChild(maxAmountInput);
                    amountFieldsDiv.appendChild(maxAmountDiv);
                    
                    withdrawalCardDiv.appendChild(amountFieldsDiv);
                    
                    // Max balance field
                    const maxBalanceFieldDiv = document.createElement('div');
                    maxBalanceFieldDiv.className = 'config-field';
                    
                    const maxBalanceLabel = document.createElement('label');
                    maxBalanceLabel.className = 'field-label';
                    maxBalanceLabel.textContent = 'Max balance';
                    maxBalanceFieldDiv.appendChild(maxBalanceLabel);
                    
                    const maxBalanceInput = document.createElement('input');
                    maxBalanceInput.type = 'number';
                    maxBalanceInput.step = '0.0001';
                    maxBalanceInput.className = 'field-input';
                    maxBalanceInput.value = withdrawalConfig.max_balance || 0.005;
                    maxBalanceInput.dataset.configPath = `${key}.withdrawals[0].max_balance`;
                    maxBalanceInput.dataset.type = 'float';
                    
                    maxBalanceFieldDiv.appendChild(maxBalanceInput);
                    withdrawalCardDiv.appendChild(maxBalanceFieldDiv);
                    
                    // Horizontal layout for checkboxes and related fields
                    const optionsFieldsDiv = document.createElement('div');
                    optionsFieldsDiv.className = 'config-field';
                    optionsFieldsDiv.style.display = 'flex';
                    optionsFieldsDiv.style.flexWrap = 'wrap';
                    optionsFieldsDiv.style.gap = '20px';
                    
                    // Wait for funds checkbox
                    const waitFundsDiv = document.createElement('div');
                    waitFundsDiv.className = 'checkbox-field';
                    waitFundsDiv.style.flex = '1';
                    
                    const waitFundsInput = document.createElement('input');
                    waitFundsInput.type = 'checkbox';
                    waitFundsInput.className = 'checkbox-input';
                    waitFundsInput.checked = withdrawalConfig.wait_for_funds || false;
                    waitFundsInput.dataset.configPath = `${key}.withdrawals[0].wait_for_funds`;
                    waitFundsInput.id = `checkbox-wait-funds`;
                    
                    const waitFundsLabel = document.createElement('label');
                    waitFundsLabel.className = 'checkbox-label';
                    waitFundsLabel.textContent = 'Wait for funds';
                    waitFundsLabel.htmlFor = waitFundsInput.id;
                    
                    waitFundsDiv.appendChild(waitFundsInput);
                    waitFundsDiv.appendChild(waitFundsLabel);
                    optionsFieldsDiv.appendChild(waitFundsDiv);
                    
                    // Max wait time field
                    const maxWaitTimeDiv = document.createElement('div');
                    maxWaitTimeDiv.style.flex = '1';
                    maxWaitTimeDiv.style.minWidth = '200px';
                    
                    const maxWaitTimeLabel = document.createElement('label');
                    maxWaitTimeLabel.className = 'field-label';
                    maxWaitTimeLabel.textContent = 'Max wait time';
                    maxWaitTimeDiv.appendChild(maxWaitTimeLabel);
                    
                    const maxWaitTimeInput = document.createElement('input');
                    maxWaitTimeInput.type = 'number';
                    maxWaitTimeInput.className = 'field-input';
                    maxWaitTimeInput.value = withdrawalConfig.max_wait_time || 99999;
                    maxWaitTimeInput.dataset.configPath = `${key}.withdrawals[0].max_wait_time`;
                    maxWaitTimeInput.dataset.type = 'number';
                    
                    maxWaitTimeDiv.appendChild(maxWaitTimeInput);
                    optionsFieldsDiv.appendChild(maxWaitTimeDiv);
                    
                    // Retries field
                    const retriesDiv = document.createElement('div');
                    retriesDiv.style.flex = '1';
                    retriesDiv.style.minWidth = '200px';
                    
                    const retriesLabel = document.createElement('label');
                    retriesLabel.className = 'field-label';
                    retriesLabel.textContent = 'Retries';
                    retriesDiv.appendChild(retriesLabel);
                    
                    const retriesInput = document.createElement('input');
                    retriesInput.type = 'number';
                    retriesInput.className = 'field-input small-input';
                    retriesInput.value = withdrawalConfig.retries || 3;
                    retriesInput.dataset.configPath = `${key}.withdrawals[0].retries`;
                    retriesInput.dataset.type = 'number';
                    
                    retriesDiv.appendChild(retriesInput);
                    optionsFieldsDiv.appendChild(retriesDiv);
                    
                    withdrawalCardDiv.appendChild(optionsFieldsDiv);
                    
                    cardsContainer.appendChild(withdrawalCardDiv);
                }
            }
        }
        
        container.appendChild(section);
    });
}

// Функция для создания карточки
function createCard(container, title, iconClass, fields, category) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'config-card';
    
    const titleDiv = document.createElement('div');
    titleDiv.className = 'card-title';
    
    const icon = document.createElement('i');
    icon.className = `fas fa-${iconClass}`;
    titleDiv.appendChild(icon);
    
    const titleText = document.createElement('span');
    titleText.textContent = title;
    titleDiv.appendChild(titleText);
    
    cardDiv.appendChild(titleDiv);
    
    fields.forEach(({ key, value, isList, isSpaceList, isRange, isBoolean, isNumber }) => {
        if (isBoolean || typeof value === 'boolean') {
            createCheckboxField(cardDiv, key, value, `${category}.${key}`);
        } else if (isRange || (Array.isArray(value) && value.length === 2 && typeof value[0] === 'number' && typeof value[1] === 'number')) {
            createRangeField(cardDiv, key, value, `${category}.${key}`);
        } else if (isList || (Array.isArray(value) && !isRange)) {
            createTagsField(cardDiv, key, value, `${category}.${key}`, isSpaceList);
        } else if (isNumber || typeof value === 'number') {
            createTextField(cardDiv, key, value, `${category}.${key}`);
        } else {
            createTextField(cardDiv, key, value, `${category}.${key}`);
        }
    });
    
    container.appendChild(cardDiv);
}

// Создание текстового поля
function createTextField(container, key, value, path) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'config-field';
    
    const label = document.createElement('label');
    label.className = 'field-label';
    label.textContent = formatFieldName(key);
    fieldDiv.appendChild(label);
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'field-input';
    input.value = value;
    input.dataset.configPath = path;
    
    if (typeof value === 'number') {
        input.dataset.type = 'number';
        input.type = 'number';
        input.className += ' small-input';
    }
    
    fieldDiv.appendChild(input);
    container.appendChild(fieldDiv);
}

// Создание поля диапазона
function createRangeField(container, key, value, path) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'config-field';
    
    const label = document.createElement('label');
    label.className = 'field-label';
    label.textContent = formatFieldName(key);
    fieldDiv.appendChild(label);
    
    // Check if this is a float value field (used in EXCHANGES and CRUSTY_SWAP)
    const isFloatField = path.includes('min_amount') || 
                          path.includes('max_amount') || 
                          path.includes('max_balance') || 
                          path.includes('AMOUNT_TO_REFUEL') ||
                          path.includes('MINIMUM_BALANCE_TO_REFUEL') ||
                          path.includes('BRIDGE_ALL_MAX_AMOUNT');
    
    // For single values that need to be treated as ranges (withdrawal settings)
    if (!Array.isArray(value)) {
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'field-input small-input';
        input.value = value;
        input.dataset.configPath = path;
        
        if (isFloatField) {
            input.step = '0.0001';
            input.dataset.type = 'float';
        } else {
            input.dataset.type = 'number';
        }
        
        fieldDiv.appendChild(input);
        container.appendChild(fieldDiv);
        return;
    }
    
    const rangeDiv = document.createElement('div');
    rangeDiv.className = 'range-input';
    
    const minInput = document.createElement('input');
    minInput.type = 'number';
    minInput.className = 'field-input range-min small-input';
    minInput.value = value[0];
    minInput.dataset.configPath = `${path}_MIN`;
    
    if (isFloatField) {
        minInput.step = '0.0001';
        minInput.dataset.type = 'float';
    } else {
        minInput.dataset.type = 'number';
    }
    
    const separator = document.createElement('span');
    separator.className = 'range-separator';
    separator.textContent = '-';
    
    const maxInput = document.createElement('input');
    maxInput.type = 'number';
    maxInput.className = 'field-input range-max small-input';
    maxInput.value = value[1];
    maxInput.dataset.configPath = `${path}_MAX`;
    
    if (isFloatField) {
        maxInput.step = '0.0001';
        maxInput.dataset.type = 'float';
    } else {
        maxInput.dataset.type = 'number';
    }
    
    rangeDiv.appendChild(minInput);
    rangeDiv.appendChild(separator);
    rangeDiv.appendChild(maxInput);
    
    fieldDiv.appendChild(rangeDiv);
    container.appendChild(fieldDiv);
}

// Создание чекбокса
function createCheckboxField(container, key, value, path) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'checkbox-field';
    
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.className = 'checkbox-input';
    input.checked = value;
    input.dataset.configPath = path;
    input.id = `checkbox-${path.replace(/\./g, '-')}`;
    
    const label = document.createElement('label');
    label.className = 'checkbox-label';
    label.textContent = formatFieldName(key);
    label.htmlFor = input.id;
    
    fieldDiv.appendChild(input);
    fieldDiv.appendChild(label);
    container.appendChild(fieldDiv);
}

// Создание списка
function createListField(container, key, value, path) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'config-field';
    
    const label = document.createElement('label');
    label.className = 'field-label';
    label.textContent = formatFieldName(key);
    fieldDiv.appendChild(label);
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'field-input list-input';
    input.value = value.join(', ');
    input.dataset.configPath = path;
    
    // Определяем, является ли это списком чисел
    if (value.length > 0 && typeof value[0] === 'number') {
        input.dataset.type = 'number-list';
    }
    
    fieldDiv.appendChild(input);
    container.appendChild(fieldDiv);
}

// Создание поля с тегами (для списков)
function createTagsField(container, key, value, path, useSpaces) {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'config-field';
    
    const label = document.createElement('label');
    label.className = 'field-label';
    label.textContent = formatFieldName(key);
    fieldDiv.appendChild(label);
    
    const tagsContainer = document.createElement('div');
    tagsContainer.className = 'tags-input';
    tagsContainer.dataset.configPath = path;
    tagsContainer.dataset.useSpaces = useSpaces ? 'true' : 'false';
    
    // Убедимся, что value является массивом
    const values = Array.isArray(value) ? value : [value];
    
    // Добавляем существующие теги
    values.forEach(item => {
        if (item !== null && item !== undefined) {
            const tag = createTag(item.toString());
            tagsContainer.appendChild(tag);
        }
    });
    
    // Добавляем поле ввода для новых тегов
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Add item...';
    
    // Обработчик для добавления нового тега
    input.addEventListener('keydown', function(e) {
        if ((e.key === 'Enter') || (e.key === ' ' && useSpaces)) {
            e.preventDefault();
            const value = this.value.trim();
            if (value) {
                const tag = createTag(value);
                tagsContainer.insertBefore(tag, this);
                this.value = '';
            }
        }
    });
    
    tagsContainer.appendChild(input);
    
    // Функция для создания тега
    function createTag(text) {
        const tag = document.createElement('div');
        tag.className = 'tag';
        
        const tagText = document.createElement('span');
        tagText.className = 'tag-text';
        tagText.textContent = text;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'tag-remove';
        removeBtn.innerHTML = '&times;';
        removeBtn.addEventListener('click', function() {
            tag.remove();
        });
        
        tag.appendChild(tagText);
        tag.appendChild(removeBtn);
        
        return tag;
    }
    
    fieldDiv.appendChild(tagsContainer);
    container.appendChild(fieldDiv);
}

// Функция для отображения уведомления
function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.className = `notification ${type} show`;
    
    document.getElementById('notification-message').textContent = message;
    
    setTimeout(() => {
        notification.className = 'notification';
    }, 3000);
}
