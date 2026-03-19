// ==============================================================================
// Copyright (C) 2019 - Philip Paquette, Steven Bocco
//
//  This program is free software: you can redistribute it and/or modify it under
//  the terms of the GNU Affero General Public License as published by the Free
//  Software Foundation, either version 3 of the License, or (at your option) any
//  later version.
//
//  This program is distributed in the hope that it will be useful, but WITHOUT
//  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
//  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
//  details.
//
//  You should have received a copy of the GNU Affero General Public License along
//  with this program.  If not, see <https://www.gnu.org/licenses/>.
// ==============================================================================
import $ from "jquery";
import {STRINGS} from "../../diplomacy/utils/strings";
import {Game} from "../../diplomacy/engine/game";

const ENABLE_LOCAL_BUNDLE_SEARCH_LOGS = process.env.REACT_APP_ENABLE_LOCAL_BUNDLE_SEARCH_LOGS === 'true';

function getValueOrEmpty(value) {
    return value == null ? '' : `${value}`;
}

function parseCsvLine(line) {
    const values = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; ++i) {
        const char = line[i];
        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                current += '"';
                ++i;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            values.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    values.push(current);
    return values;
}

function parseBundleSearchCsv(csvText) {
    const lines = csvText.split(/\r?\n/).filter(Boolean);
    if (!lines.length)
        return [];
    const headers = parseCsvLine(lines[0]);
    return lines.slice(1).map(line => {
        const values = parseCsvLine(line);
        const row = {};
        headers.forEach((header, index) => {
            row[header] = getValueOrEmpty(values[index]);
        });
        return row;
    });
}

async function getBundleSearchDirectoryHandle(gameId) {
    if (typeof window.showDirectoryPicker !== 'function')
        return null;
    let selectedDirectory = null;
    try {
        selectedDirectory = await window.showDirectoryPicker({mode: 'read'});
    } catch (error) {
        return null;
    }
    if (selectedDirectory.name === `${gameId}`)
        return selectedDirectory;
    try {
        return await selectedDirectory.getDirectoryHandle(`${gameId}`);
    } catch (error) {
        return null;
    }
}

async function loadBundleSearchLogs(gameId) {
    if (!ENABLE_LOCAL_BUNDLE_SEARCH_LOGS)
        return {};
    const shouldLoadLogs = window.confirm(
        `Load bundle search logs for ${gameId}? Select logs/ or logs/${gameId} in the next dialog.`
    );
    if (!shouldLoadLogs)
        return {};
    const directoryHandle = await getBundleSearchDirectoryHandle(gameId);
    if (!directoryHandle)
        return {};

    const bundleSearchLogs = {};
    for await (const entry of directoryHandle.values()) {
        if (entry.kind !== 'file' || !entry.name.match(/\.csv$/i))
            continue;
        const file = await entry.getFile();
        const phaseName = entry.name.replace(/\.csv$/i, '');
        bundleSearchLogs[phaseName] = parseBundleSearchCsv(await file.text());
    }
    return bundleSearchLogs;
}

export function loadGameFromDisk() {
    return new Promise((onLoad, onError) => {
        const input = $(document.createElement('input'));
        input.attr("type", "file");
        input.trigger('click');
        input.change(event => {
            const file = event.target.files[0];
            if (!file.name.match(/\.json$/i)) {
                onError(`Invalid JSON filename ${file.name}`);
                return;
            }
            const reader = new FileReader();
            reader.onload = async () => {
                const savedData = JSON.parse(reader.result);
                const gameObject = {};
                gameObject.game_id = `(local) ${savedData.id}`;
                gameObject.map_name = savedData.map;
                gameObject.rules = savedData.rules;
                gameObject.state_history = {};
                gameObject.message_history = {};
                gameObject.order_history = {};
                gameObject.result_history = {};

                // Load all saved phases (expect the latest one) to history fields.
                for (let i = 0; i < savedData.phases.length - 1; ++i) {
                    const savedPhase = savedData.phases[i];
                    const gameState = savedPhase.state;
                    const phaseOrders = savedPhase.orders || {};
                    const phaseResults = savedPhase.results || {};
                    const phaseMessages = {};
                    if (savedPhase.messages) {
                        for (let message of savedPhase.messages) {
                            phaseMessages[message.time_sent] = message;
                        }
                    }
                    if (!gameState.name)
                        gameState.name = savedPhase.name;
                    gameObject.state_history[gameState.name] = gameState;
                    gameObject.message_history[gameState.name] = phaseMessages;
                    gameObject.order_history[gameState.name] = phaseOrders;
                    gameObject.result_history[gameState.name] = phaseResults;
                }

                // Load latest phase separately and use it later to define the current game phase.
                const latestPhase = savedData.phases[savedData.phases.length - 1];
                const latestGameState = latestPhase.state;
                const latestPhaseOrders = latestPhase.orders || {};
                const latestPhaseResults = latestPhase.results || {};
                const latestPhaseMessages = {};
                if (latestPhase.messages) {
                    for (let message of latestPhase.messages) {
                        latestPhaseMessages[message.time_sent] = message;
                    }
                }
                if (!latestGameState.name)
                    latestGameState.name = latestPhase.name;
                // TODO: NB: What if latest phase in loaded JSON contains order results? Not sure if it is well handled.
                gameObject.result_history[latestGameState.name] = latestPhaseResults;

                gameObject.messages = [];
                gameObject.role = STRINGS.OBSERVER_TYPE;
                gameObject.status = STRINGS.COMPLETED;
                gameObject.timestamp_created = 0;
                gameObject.deadline = 0;
                gameObject.n_controls = 0;
                gameObject.registration_password = '';
                gameObject.bundle_search_logs = await loadBundleSearchLogs(savedData.id);
                const game = new Game(gameObject);

                // Set game current phase and state using latest phase found in JSON file.
                game.setPhaseData({
                    name: latestGameState.name,
                    state: latestGameState,
                    orders: latestPhaseOrders,
                    messages: latestPhaseMessages
                });
                onLoad(game);
            };
            reader.readAsText(file);
        });
    });
}
