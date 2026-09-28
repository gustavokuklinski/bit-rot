/**
 * BIT ROT Survival Database - GitHub Pages Realtime Directory Engine
 * Scans repository trees and fetches raw XMLs straight from static hosting.
 */

class BitRotWiki {
    constructor() {
        this.domParser = new DOMParser();
        this.rawFiles = new Map(); // filename -> raw XML String
        
        // Entity collections
        this.items = new Map();
        this.clothes = new Map();
        this.recipes = [];

        // Cross-reference graphs
        this.craftedBy = new Map();
        this.usedIn = new Map();
        this.repairedBy = new Map();
        this.dismantledTo = new Map();
        this.containedIn = new Map();

        this.activeFilter = 'all';
        this.searchQuery = '';

        this.init();
    }

    init() {
        this.bindEvents();
        this.autoDetectAndFetch();
    }

    bindEvents() {
        window.addEventListener('hashchange', () => this.handleRoute());

        document.getElementById('btn-gh-fetch').addEventListener('click', () => {
            const repoVal = document.getElementById('gh-repo-input').value.trim();
            if (repoVal) this.fetchRepoFiles(repoVal);
        });

        document.getElementById('search-input').addEventListener('input', (e) => {
            this.searchQuery = e.target.value.toLowerCase().trim();
            this.renderNavList();
        });

        document.getElementById('clear-search').addEventListener('click', () => {
            const input = document.getElementById('search-input');
            input.value = '';
            this.searchQuery = '';
            this.renderNavList();
        });

        document.querySelectorAll('.filter-tabs .tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-tabs .tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                this.activeFilter = e.target.dataset.filter;
                this.renderNavList();
            });
        });
    }

    /**
     * Inspects window.location to determine if we are hosted on a github.io domain
     */
    autoDetectAndFetch() {
        const host = window.location.hostname;
        const pathSegments = window.location.pathname.split('/').filter(Boolean);

        let owner = '';
        let repo = '';

        if (host.endsWith('github.io')) {
            // e.g. username.github.io/reponame/
            owner = host.replace('.github.io', '');
            repo = pathSegments[0] || '';
        }

        if (owner && repo) {
            const fullRepo = `${owner}/${repo}`;
            document.getElementById('gh-repo-input').value = fullRepo;
            this.fetchRepoFiles(fullRepo);
        } else {
            this.setConnectionStatus("Enter username/repo to load", false);
            this.renderEmptyState();
        }
    }

    /**
     * Queries GitHub Git Trees API to find all files recursively in one call
     */
    async fetchRepoFiles(repoFull) {
        this.setConnectionStatus(`Discovering files in ${repoFull}...`, false);
        this.showProgress(0, "Connecting...");

        const branches = ['main', 'master'];
        let treeData = null;

        for (const branch of branches) {
            try {
                const res = await fetch(`https://api.github.com/repos/${repoFull}/git/trees/${branch}?recursive=1`);
                if (res.ok) {
                    treeData = await res.json();
                    break;
                }
            } catch (err) {
                console.warn(`Branch ${branch} check failed:`, err);
            }
        }

        if (!treeData || !treeData.tree) {
            this.hideProgress();
            this.setConnectionStatus("Could not read repo tree", false);
            alert(`Unable to access repo: ${repoFull}. Verify that the repository is public.`);
            return;
        }

        // Filter only XML files in your data folder
        const xmlNodes = treeData.tree.filter(node => 
            node.type === 'blob' && 
            node.path.endsWith('.xml') &&
            node.path.includes('data')
        );

        if (!xmlNodes.length) {
            this.hideProgress();
            this.setConnectionStatus("No XMLs found in data folder", false);
            alert("No XML files detected matching the path pattern.");
            return;
        }

        this.rawFiles.clear();
        let loaded = 0;
        const total = xmlNodes.length;

        // Fetch XML file bodies concurrently via static relative path
        const concurrency = 8;
        const queue = [...xmlNodes];

        const worker = async () => {
            while (queue.length > 0) {
                const node = queue.shift();
                const fileName = node.path.split('/').pop();
                
                // Fetch directly from your GitHub Pages host
                const relativeUrl = `./${node.path}`;
                try {
                    const res = await fetch(relativeUrl);
                    if (res.ok) {
                        const text = await res.text();
                        this.rawFiles.set(fileName, text);
                    }
                } catch (e) {
                    console.warn(`Failed loading ${relativeUrl}`, e);
                }

                loaded++;
                const pct = Math.round((loaded / total) * 100);
                this.showProgress(pct, `Loading: ${loaded}/${total}`);
            }
        };

        const workers = Array.from({ length: concurrency }, () => worker());
        await Promise.all(workers);

        this.hideProgress();
        this.rebuildDatabase();
    }

    showProgress(percent, label) {
        const container = document.getElementById('load-progress-container');
        const bar = document.getElementById('load-progress-bar');
        const text = document.getElementById('load-progress-text');
        container.style.display = 'block';
        bar.style.width = `${percent}%`;
        text.textContent = label;
    }

    hideProgress() {
        document.getElementById('load-progress-container').style.display = 'none';
    }

    /**
     * Parses the downloaded XML strings and forms cross-reference links
     */
    rebuildDatabase() {
        this.items.clear();
        this.clothes.clear();
        this.recipes = [];
        this.craftedBy.clear();
        this.usedIn.clear();
        this.repairedBy.clear();
        this.dismantledTo.clear();
        this.containedIn.clear();

        for (const [filename, xmlString] of this.rawFiles.entries()) {
            try {
                const xmlDoc = this.domParser.parseFromString(xmlString, "application/xml");
                if (xmlDoc.querySelector("parsererror")) {
                    console.warn(`XML syntax error in: ${filename}`);
                    continue;
                }
                this.parseXmlFile(filename, xmlDoc, xmlString);
            } catch (err) {
                console.error(`Error parsing ${filename}:`, err);
            }
        }

        this.buildCrossReferences();
        this.setConnectionStatus(`Connected (${this.rawFiles.size} XMLs)`, true);
        this.updateStats();
        this.renderNavList();

        if (window.location.hash) {
            this.handleRoute();
        } else {
            this.renderHome();
        }
    }

    parseXmlFile(filename, doc, rawXml) {
        const root = doc.documentElement;
        const tag = root.tagName.toLowerCase();

        if (tag === 'item') {
            const item = {
                category: 'item',
                filename,
                rawXml,
                name: root.getAttribute('name') || filename.replace('.xml',''),
                type: root.getAttribute('type') || 'generic',
                allow_belt: root.getAttribute('allow_belt') === 'true',
                allow_liquid: root.getAttribute('allow_liquid') === 'true',
                disposable: root.getAttribute('disposable') === 'true',
                consume_time: root.getAttribute('consume_time'),
                tip: root.getAttribute('tip'),
                spawn_chance: root.querySelector('spawn')?.getAttribute('chance'),
                properties: this.extractKeyValues(root.querySelector('properties')),
                loot: this.extractLoot(root.querySelector('loot')),
                attributes: this.extractKeyValues(root.querySelector('attributes')),
                sound: this.extractKeyValues(root.querySelector('sound'))
            };
            this.items.set(item.name, item);
        }
        else if (tag === 'cloth') {
            const cloth = {
                category: 'cloth',
                filename,
                rawXml,
                name: root.getAttribute('name') || filename.replace('.xml',''),
                type: 'cloth',
                slot: root.getAttribute('id') || 'misc',
                builder: root.getAttribute('builder') === 'true',
                hide_cloth: root.getAttribute('hide_cloth'),
                spawn_chance: root.querySelector('spawn')?.getAttribute('chance'),
                properties: this.extractKeyValues(root.querySelector('properties')),
                loot: this.extractLoot(root.querySelector('loot'))
            };
            this.clothes.set(cloth.name, cloth);
        }
        else if (tag === 'recipe') {
            const recipe = {
                category: 'recipe',
                filename,
                rawXml,
                type: root.getAttribute('type') || 'craft',
                craft: root.getAttribute('craft') || 'create',
                outputRaw: root.getAttribute('output') || '',
                magazine: root.getAttribute('magazine'),
                req_level: root.getAttribute('req_level'),
                gain_xp: root.getAttribute('gain_xp'),
                amount: root.getAttribute('amount') || '1',
                time: root.getAttribute('time') || '0',
                ingredients: [],
                results: []
            };

            recipe.outputs = this.extractRecipeOutputs(recipe.outputRaw);

            root.querySelectorAll('ingredient').forEach(ing => {
                const rawName = ing.getAttribute('name') || '';
                recipe.ingredients.push({
                    nameRaw: rawName,
                    names: this.parseOptionNames(rawName),
                    amount: ing.getAttribute('amount') || '1',
                    destroy: ing.getAttribute('destroy') !== 'false'
                });
            });

            root.querySelectorAll('result').forEach(res => {
                const rawName = res.getAttribute('name') || '';
                recipe.results.push({
                    nameRaw: rawName,
                    names: this.parseOptionNames(rawName),
                    amount: res.getAttribute('amount') || '1',
                    chance: res.getAttribute('chance') || '1.0'
                });
            });

            this.recipes.push(recipe);
        }
    }

    extractKeyValues(node) {
        if (!node) return {};
        const data = {};
        for (const child of node.children) {
            const key = child.tagName;
            const attrs = {};
            for (const attr of child.attributes) attrs[attr.name] = attr.value;
            data[key] = attrs;
        }
        return data;
    }

    extractLoot(node) {
        if (!node) return [];
        const items = [];
        node.querySelectorAll('item').forEach(it => {
            items.push({
                name: it.getAttribute('name'),
                chance: it.getAttribute('chance') || '1.0'
            });
        });
        return items;
    }

    parseOptionNames(str) {
        if (!str) return [];
        str = str.trim();
        if (str.startsWith('[') && str.endsWith(']')) {
            return str.slice(1, -1).split(',').map(s => s.trim()).filter(Boolean);
        }
        return [str];
    }

    extractRecipeOutputs(outputStr) {
        if (!outputStr) return [];
        if (outputStr.includes('baseItem:')) {
            const baseMatch = outputStr.match(/baseItem:([^},]+)/);
            if (baseMatch) return [baseMatch[1].trim()];
        }
        return [outputStr.trim()];
    }

    buildCrossReferences() {
        const add = (map, k, v) => {
            if (!map.has(k)) map.set(k, []);
            map.get(k).push(v);
        };

        this.recipes.forEach(r => {
            if (r.craft === 'create') {
                r.outputs.forEach(out => add(this.craftedBy, out, r));
            } else if (r.craft === 'repair') {
                r.outputs.forEach(out => add(this.repairedBy, out, r));
            } else if (r.craft === 'dismantle') {
                r.ingredients.forEach(ing => ing.names.forEach(n => add(this.dismantledTo, n, r)));
            }

            r.ingredients.forEach(ing => ing.names.forEach(n => add(this.usedIn, n, r)));
        });

        const indexLoot = (owner, lootList) => {
            lootList.forEach(drop => add(this.containedIn, drop.name, owner));
        };

        this.items.forEach(i => indexLoot(i.name, i.loot));
        this.clothes.forEach(c => indexLoot(c.name, c.loot));
    }

    setConnectionStatus(text, isOk) {
        const badge = document.getElementById('connection-status');
        badge.textContent = text;
        badge.className = `status-badge ${isOk ? 'status-connected' : 'status-disconnected'}`;
    }

    updateStats() {
        const count = this.items.size + this.clothes.size + this.recipes.length;
        document.getElementById('stat-counter').textContent = 
            `${count} Loaded (${this.items.size} Items, ${this.clothes.size} Clothes, ${this.recipes.length} Crafts)`;
    }

    renderEmptyState() {
        document.getElementById('wiki-viewport').innerHTML = `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:60vh; text-align:center;">
                <div style="font-size:3rem; margin-bottom:16px;">🌐</div>
                <h2>Connect to GitHub Pages Repository</h2>
                <p style="color:var(--text-secondary); max-width:480px; margin-top:8px;">
                    Enter your repository in the format <code>username/repository</code> in the sidebar and click <b>Fetch</b> to load the files.
                </p>
            </div>
        `;
    }

    renderNavList() {
        const listEl = document.getElementById('nav-list');
        listEl.innerHTML = '';

        const all = [];
        if (this.activeFilter === 'all' || this.activeFilter === 'item') {
            this.items.forEach(i => all.push({ name: i.name, type: i.type, cat: 'item', entity: i }));
        }
        if (this.activeFilter === 'all' || this.activeFilter === 'cloth') {
            this.clothes.forEach(c => all.push({ name: c.name, type: `cloth: ${c.slot}`, cat: 'cloth', entity: c }));
        }
        if (this.activeFilter === 'all' || this.activeFilter === 'recipe') {
            this.recipes.forEach(r => {
                const name = r.outputs.length ? `${r.craft}: ${r.outputs.join(', ')}` : `${r.craft} (${r.filename})`;
                all.push({ name, type: r.type, cat: 'recipe', entity: r });
            });
        }

        const filtered = all.filter(e => {
            if (!this.searchQuery) return true;
            return e.name.toLowerCase().includes(this.searchQuery) || e.type.toLowerCase().includes(this.searchQuery);
        });

        filtered.sort((a,b) => a.name.localeCompare(b.name));

        const frag = document.createDocumentFragment();
        filtered.forEach(entry => {
            const a = document.createElement('a');
            a.className = 'nav-item';
            a.href = `#entity=${encodeURIComponent(entry.name)}`;

            const name = document.createElement('span');
            name.textContent = entry.name;
            name.style.overflow = 'hidden';
            name.style.textOverflow = 'ellipsis';
            name.style.whiteSpace = 'nowrap';

            const badge = document.createElement('span');
            badge.className = `badge badge-${entry.cat}`;
            badge.textContent = entry.entity.craft || entry.entity.type || entry.cat;

            a.appendChild(name);
            a.appendChild(badge);
            frag.appendChild(a);
        });

        listEl.appendChild(frag);
    }

    handleRoute() {
        const hash = decodeURIComponent(window.location.hash.slice(1));
        const viewport = document.getElementById('wiki-viewport');
        const activeCrumb = document.getElementById('active-crumb');

        if (!hash || !hash.startsWith('entity=')) {
            if (this.rawFiles.size > 0) this.renderHome();
            else this.renderEmptyState();
            activeCrumb.textContent = "Overview";
            return;
        }

        const target = hash.replace('entity=', '');
        activeCrumb.textContent = target;

        if (this.items.has(target)) {
            this.renderItemPage(this.items.get(target), viewport);
            return;
        }

        if (this.clothes.has(target)) {
            this.renderClothPage(this.clothes.get(target), viewport);
            return;
        }

        const recipe = this.recipes.find(r => 
            r.outputs.includes(target) || 
            `${r.craft}: ${r.outputs.join(', ')}` === target ||
            r.filename === target
        );

        if (recipe) {
            this.renderRecipePage(recipe, viewport);
            return;
        }

        this.renderNotFoundPage(target, viewport);
    }

    renderHome() {
        const container = document.getElementById('wiki-viewport');
        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">Bit Rot Database</h1>
                <p style="color:var(--text-secondary); margin-top:6px;">Live repository index and cross-referencer.</p>
            </div>
            <div class="wiki-grid">
                <div class="wiki-main">
                    <div class="section">
                        <h2 class="section-title">📦 Database Categories</h2>
                        <div class="cards-container">
                            <div class="wiki-card" onclick="document.querySelector('.tab[data-filter=item]').click()">
                                <div class="wiki-card-title">Items (${this.items.size})</div>
                                <p style="font-size:0.8rem; color:var(--text-secondary)">Weapons, ammunition, tools, and consumables.</p>
                            </div>
                            <div class="wiki-card" onclick="document.querySelector('.tab[data-filter=cloth]').click()">
                                <div class="wiki-card-title">Clothes & Armor (${this.clothes.size})</div>
                                <p style="font-size:0.8rem; color:var(--text-secondary)">Wearable apparel, capacity, and defence properties.</p>
                            </div>
                            <div class="wiki-card" onclick="document.querySelector('.tab[data-filter=recipe]').click()">
                                <div class="wiki-card-title">Crafting & Salvage (${this.recipes.length})</div>
                                <p style="font-size:0.8rem; color:var(--text-secondary)">Crafting schematics, repairs, and salvage yields.</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="wiki-sidebar">
                    <div class="infobox">
                        <div class="infobox-header">Repository Status</div>
                        <div class="infobox-content">
                            <div class="infobox-row"><span class="infobox-label">Items</span><span class="infobox-value">${this.items.size}</span></div>
                            <div class="infobox-row"><span class="infobox-label">Clothes</span><span class="infobox-value">${this.clothes.size}</span></div>
                            <div class="infobox-row"><span class="infobox-label">Recipes</span><span class="infobox-value">${this.recipes.length}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderItemPage(item, container) {
        const craftedList = this.craftedBy.get(item.name) || [];
        const usedList = this.usedIn.get(item.name) || [];
        const repairList = this.repairedBy.get(item.name) || [];
        const dismantleList = this.dismantledTo.get(item.name) || [];
        const containedInList = this.containedIn.get(item.name) || [];

        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">
                    <span>${this.escapeHtml(item.name)}</span>
                    <span class="badge badge-item">${item.type}</span>
                </h1>
                ${item.tip ? `<div class="tip-banner">💡 ${this.escapeHtml(item.tip)}</div>` : ''}
            </div>

            <div class="wiki-grid">
                <div class="wiki-main">
                    ${this.renderRecipeSection("🔨 How to Craft", craftedList)}
                    ${this.renderRecipeSection("🔧 How to Repair", repairList)}
                    ${this.renderRecipeSection("♻️ Dismantling / Scrapping", dismantleList)}
                    ${this.renderRecipeSection("⚙️ Used in Recipes as Ingredient / Tool", usedList)}
                    ${this.renderContainedInSection(containedInList)}
                    
                    <div class="section">
                        <h3 class="section-title">📄 Raw XML Source (${item.filename})</h3>
                        <pre class="raw-xml-viewer">${this.escapeHtml(item.rawXml)}</pre>
                    </div>
                </div>

                <div class="wiki-sidebar">
                    <div class="infobox">
                        <div class="infobox-header">Item Specs</div>
                        <div class="infobox-content">
                            <div class="infobox-row"><span class="infobox-label">Type</span><span class="infobox-value">${item.type}</span></div>
                            <div class="infobox-row"><span class="infobox-label">Belt Usable</span><span class="infobox-value">${item.allow_belt ? "Yes" : "No"}</span></div>
                            ${this.renderPropertyRows(item.properties)}
                            ${item.consume_time ? `<div class="infobox-row"><span class="infobox-label">Use Time</span><span class="infobox-value">${item.consume_time}s</span></div>` : ''}
                            ${item.spawn_chance ? `<div class="infobox-row"><span class="infobox-label">Spawn Chance</span><span class="infobox-value">${item.spawn_chance}</span></div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderClothPage(cloth, container) {
        const repairList = this.repairedBy.get(cloth.name) || [];
        const usedList = this.usedIn.get(cloth.name) || [];
        const dismantleList = this.dismantledTo.get(cloth.name) || [];

        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">
                    <span>${this.escapeHtml(cloth.name)}</span>
                    <span class="badge badge-cloth">${cloth.slot}</span>
                </h1>
            </div>

            <div class="wiki-grid">
                <div class="wiki-main">
                    ${this.renderRecipeSection("🔧 Repair Recipes", repairList)}
                    ${this.renderRecipeSection("♻️ Dismantling / Scrapping", dismantleList)}
                    ${this.renderRecipeSection("⚙️ Used in Crafting", usedList)}

                    ${cloth.loot && cloth.loot.length ? `
                        <div class="section">
                            <h3 class="section-title">🎁 Pocket Loot Drops</h3>
                            <ul class="ingredient-list">
                                ${cloth.loot.map(l => `
                                    <li class="ingredient-item">
                                        ${this.makeWikiLink(l.name)}
                                        <span class="badge">Chance: ${(parseFloat(l.chance)*100).toFixed(0)}%</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    <div class="section">
                        <h3 class="section-title">📄 Raw XML Source (${cloth.filename})</h3>
                        <pre class="raw-xml-viewer">${this.escapeHtml(cloth.rawXml)}</pre>
                    </div>
                </div>

                <div class="wiki-sidebar">
                    <div class="infobox">
                        <div class="infobox-header">Clothing Attributes</div>
                        <div class="infobox-content">
                            <div class="infobox-row"><span class="infobox-label">Slot</span><span class="infobox-value">${cloth.slot}</span></div>
                            <div class="infobox-row"><span class="infobox-label">Builder</span><span class="infobox-value">${cloth.builder ? "Yes" : "No"}</span></div>
                            ${this.renderPropertyRows(cloth.properties)}
                            ${cloth.hide_cloth ? `<div class="infobox-row"><span class="infobox-label">Hides</span><span class="infobox-value">${cloth.hide_cloth}</span></div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderRecipePage(recipe, container) {
        const title = recipe.outputs.length ? recipe.outputs.join(', ') : `${recipe.craft} (${recipe.filename})`;

        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">
                    <span>${this.escapeHtml(title)}</span>
                    <span class="badge badge-${recipe.craft}">${recipe.craft}</span>
                </h1>
            </div>

            <div class="wiki-grid">
                <div class="wiki-main">
                    <div class="section">
                        <h3 class="section-title">📋 Crafting Schematic</h3>
                        ${this.renderSingleRecipeCard(recipe, false)}
                    </div>
                    <div class="section">
                        <h3 class="section-title">📄 Raw Recipe XML (${recipe.filename})</h3>
                        <pre class="raw-xml-viewer">${this.escapeHtml(recipe.rawXml)}</pre>
                    </div>
                </div>

                <div class="wiki-sidebar">
                    <div class="infobox">
                        <div class="infobox-header">Recipe Parameters</div>
                        <div class="infobox-content">
                            <div class="infobox-row"><span class="infobox-label">Action</span><span class="infobox-value">${recipe.craft}</span></div>
                            <div class="infobox-row"><span class="infobox-label">Craft Time</span><span class="infobox-value">${recipe.time}s</span></div>
                            <div class="infobox-row"><span class="infobox-label">Yield Amount</span><span class="infobox-value">x${recipe.amount}</span></div>
                            ${recipe.magazine ? `<div class="infobox-row"><span class="infobox-label">Required Guide</span><span class="infobox-value">${this.makeWikiLink(recipe.magazine)}</span></div>` : ''}
                            ${recipe.req_level ? `<div class="infobox-row"><span class="infobox-label">Req. Skill</span><span class="infobox-value">${recipe.req_level}</span></div>` : ''}
                            ${recipe.gain_xp ? `<div class="infobox-row"><span class="infobox-label">XP Gain</span><span class="infobox-value">${recipe.gain_xp}</span></div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderNotFoundPage(name, container) {
        const usedList = this.usedIn.get(name) || [];
        const craftedList = this.craftedBy.get(name) || [];

        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">${this.escapeHtml(name)}</h1>
                <p style="color:var(--text-secondary)">Virtual Reference (Mentioned in recipes but has no individual XML definition file).</p>
            </div>
            <div class="wiki-grid">
                <div class="wiki-main">
                    ${this.renderRecipeSection("🔨 How to Craft", craftedList)}
                    ${this.renderRecipeSection("⚙️ Used in Recipes", usedList)}
                </div>
            </div>
        `;
    }

    renderRecipeSection(title, recipes) {
        if (!recipes || !recipes.length) return '';
        return `
            <div class="section">
                <h3 class="section-title">${title} (${recipes.length})</h3>
                <div class="cards-container">
                    ${recipes.map(r => this.renderSingleRecipeCard(r, true)).join('')}
                </div>
            </div>
        `;
    }

    renderContainedInSection(owners) {
        if (!owners || !owners.length) return '';
        return `
            <div class="section">
                <h3 class="section-title">📦 Found Inside Containers / Loot (${owners.length})</h3>
                <ul class="ingredient-list">
                    ${owners.map(o => `
                        <li class="ingredient-item">
                            ${this.makeWikiLink(o)}
                            <span class="badge">Container</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    renderSingleRecipeCard(recipe, isCard = true) {
        return `
            <div class="${isCard ? 'wiki-card' : ''}" style="margin-bottom:8px;">
                <div class="wiki-card-title">
                    <span>${recipe.outputs.length ? recipe.outputs.map(o => this.makeWikiLink(o)).join(', ') : recipe.filename}</span>
                    <span class="badge badge-${recipe.craft}">⏳ ${recipe.time}s</span>
                </div>
                
                ${recipe.magazine ? `<div style="font-size:0.75rem; margin-bottom:6px; color:var(--text-secondary);">Requires: ${this.makeWikiLink(recipe.magazine)}</div>` : ''}
                
                <div style="font-size:0.8rem; font-weight:600; margin-top:8px;">Ingredients:</div>
                <ul class="ingredient-list">
                    ${recipe.ingredients.map(ing => `
                        <li class="ingredient-item">
                            <span class="ingredient-links">
                                ${ing.names.map(n => this.makeWikiLink(n)).join(' <span style="color:var(--text-secondary)">or</span> ')}
                            </span>
                            <span class="badge" style="color:${ing.destroy ? '#f85149' : '#3fb950'}">
                                x${ing.amount} ${ing.destroy ? '(consumed)' : '(tool)'}
                            </span>
                        </li>
                    `).join('')}
                </ul>

                ${recipe.results && recipe.results.length ? `
                    <div style="font-size:0.8rem; font-weight:600; margin-top:8px;">Byproducts:</div>
                    <ul class="ingredient-list">
                        ${recipe.results.map(res => `
                            <li class="ingredient-item">
                                <span class="ingredient-links">
                                    ${res.names.map(n => this.makeWikiLink(n)).join(' <span style="color:var(--text-secondary)">or</span> ')}
                                </span>
                                <span class="badge">x${res.amount} (${(parseFloat(res.chance)*100).toFixed(0)}%)</span>
                            </li>
                        `).join('')}
                    </ul>
                ` : ''}

                ${recipe.gain_xp ? `<div style="font-size:0.75rem; color:#8ec2ff; margin-top:6px;">XP: ${recipe.gain_xp}</div>` : ''}
            </div>
        `;
    }

    renderPropertyRows(props) {
        if (!props) return '';
        let html = '';
        for (const [tag, attrs] of Object.entries(props)) {
            for (const [k, v] of Object.entries(attrs)) {
                const label = k === 'value' ? tag : `${tag} ${k}`;
                let displayVal = v;
                if (tag === 'ammo' && k === 'type') displayVal = this.makeWikiLink(v);
                html += `<div class="infobox-row"><span class="infobox-label">${label}</span><span class="infobox-value">${displayVal}</span></div>`;
            }
        }
        return html;
    }

    makeWikiLink(name) {
        if (!name) return '';
        return `<a class="wikilink" href="#entity=${encodeURIComponent(name.trim())}">${this.escapeHtml(name.trim())}</a>`;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.wiki = new BitRotWiki();
});