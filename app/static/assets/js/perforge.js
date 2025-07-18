(function(global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory(require('bootstrap')) : typeof define === 'function' && define.amd ? define(['bootstrap'], factory) : (global = typeof globalThis !== 'undefined' ? globalThis : global || self,
  global.perforge = factory(global.bootstrap));
}
)(this, (function() {
  'use strict';

  const docReady = e=>{
      "loading" === document.readyState ? document.addEventListener("DOMContentLoaded", e) : setTimeout(e, 1);
  };

  const camelize = e=>{
      const t = e.replace(/[-_\s.]+(.)?/g, ((e,t)=>t ? t.toUpperCase() : ""));
      return `${t.substr(0, 1).toLowerCase()}${t.substr(1)}`
  };

  const getData = (e,t)=>{
      try {
          return JSON.parse(e.dataset[camelize(t)])
      } catch (o) {
          return e.dataset[camelize(t)]
      }
  };

  const hasClass = (e,t)=>e.classList.value.includes(t);
  const addClass = (e,t)=>e.classList.add(t);
  const removeClass = (e,t)=>e.classList.remove(t);

  const setCookie = (e,t,o)=>{
      const r = new Date;
      r.setTime(r.getTime() + o),
      document.cookie = e + "=" + t + ";expires=" + r.toUTCString();
  };
  const getCookie = e=>{
      var t = document.cookie.match("(^|;) ?" + e + "=([^;]*)(;|$)");
      return t ? t[2] : t
  };
  const getRandomNumber = (e,t)=>Math.floor(Math.random() * (t - e) + e);

  const sendPostRequest = (url, json) => {
    return new Promise((resolve, reject) => {
      // Parse the JSON string if it's a string
      const data = typeof json === 'string' ? JSON.parse(json) : json;

      // Convert traditional URL to API endpoint
      const endpoint = url.replace(/^\//, '').replace(/\/(\w+)$/, '');

      // Use the API client for all POST requests
      apiClient.post(endpoint, data)
        .then((response) => {
          if (response.status === 'success') {
            // Handle redirect if available
            if (response.redirect_url) {
              resolve(response.redirect_url);
            } else {
              resolve(response);
            }
          } else {
            reject(new Error(response.message || 'Request failed'));
          }
        })
        .catch((error) => {
          reject(error);
        });
    });
  };

  const sendPostRequestReport = (url, json) => {
    return new Promise((resolve, reject) => {
      // Parse the JSON string if it's a string
      const data = typeof json === 'string' ? JSON.parse(json) : json;

      // Use the API client for report generation
      apiClient.tests.generateReport(data)
          .then((response) => {
            if (response.status === 'success') {
              showResultModal("Report generated!", response.data);
              resolve();
            } else {
              showResultModal("Failed!", response.message);
              reject(new Error(response.message));
            }
          })
          .catch((error) => {
            showResultModal("Failed!", error.message || "An error occurred while generating the report");
            reject(error);
          });
    });
  };

  const sendDownloadRequest = (url, json) => {
    return new Promise((resolve, reject) => {
        const data = typeof json === 'string' ? JSON.parse(json) : json;

        fetch('/api/v1/reports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cookie': `project=${getCookie('project')}`
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            // Get the X-Result-Data header that contains the statistics
            const resultData = response.headers.get('X-Result-Data');

            if (!response.ok) {
                return response.json().then(err => {
                    showResultModal("Failed!", err.message || "Failed to generate PDF report");
                    throw new Error(err.message || 'PDF generation failed');
                });
            }

            // Parse the result data from the header and show it in the modal
            if (resultData) {
                try {
                    const parsedData = JSON.parse(resultData);
                    showResultModal("Report generated!", parsedData);
                    resolve(parsedData);
                } catch (e) {
                    console.error("Failed to parse result data:", e);
                }
            }

            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'report.pdf';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                if (filenameMatch && filenameMatch.length > 1) {
                    filename = filenameMatch[1];
                }
            }
            return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(link.href);
            resolve();
        })
        .catch(error => {
            showResultModal("Failed!", error.message || "An error occurred while generating the report");
            reject(error);
        });
    });
  };

  const sendGetRequest = (url) => {
    return new Promise((resolve, reject) => {
      // Convert URL to API endpoint format
      let endpoint;

      if (url.startsWith('/api/v1/')) {
        // Already in the correct format
        endpoint = url.replace('/api/v1/', '');
      } else {
        // Convert traditional URL to API endpoint
        endpoint = url.replace(/^\//, '').replace(/\/(\w+)$/, '');
      }

      // Use the API client for all GET requests
      apiClient.get(endpoint)
        .then((response) => {
          resolve(response);
        })
        .catch((error) => {
          reject(error);
        });
    });
  };

  const validateForm = (form, event, callback) => {
    console.log("validateForm called with form:", form);
    console.log("validateForm called with event:", event);

    form.classList.add('was-validated');
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
        callback(false);
    } else {
        // for (let i = 0; i < form.elements.length; i++) {
        //   const element = form.elements[i];
        //   if (!element.checkValidity()) {
        //     alert(`Invalid field: ${element.name}`);
        //   }
        // }
        // If validation is successful, update button style
        event.preventDefault()
        callback(true);
    }
  };

  function showResultModal(message, result=null) {
    // Populate the modal with the result data using a loop
    const resultModalBody = document.getElementById('resultModalBody');
    const resultModalLabel = document.getElementById('resultModalLabel');
    resultModalBody.innerHTML = ''; // Clear previous content
    resultModalLabel.innerHTML = message;

    if (typeof result === 'object' && result !== null && !Array.isArray(result)) {
      // Filter out binary/large content that shouldn't be displayed
      const filteredResult = {};

      for (const [key, value] of Object.entries(result)) {
        // Skip pdf_content and blob properties
        if (key !== 'pdf_content' && key !== 'blob') {
          filteredResult[key] = value;
        }
      }

      // Check if we have any properties to display
      if (Object.keys(filteredResult).length > 0) {
        resultModalBody.style.display = 'block';

        for (const [key, value] of Object.entries(filteredResult)) {
          const p = document.createElement('p');
          p.innerHTML = `<strong>${key}:</strong> <span style="float: right; text-align: right;">${value}</span>`;
          resultModalBody.appendChild(p);
        }
      } else {
        resultModalBody.style.display = 'none';
      }
    } else if (typeof result === 'string') {
      resultModalBody.style.display = 'block';
      const p = document.createElement('p');
      p.textContent = result; // Set the text content to the string result
      p.style.whiteSpace = 'pre-wrap'; // Preserve new lines and wrap text
      resultModalBody.appendChild(p);
    } else {
      resultModalBody.style.display = 'none';
    }

    // Show the modal
    const resultModal = new bootstrap.Modal(document.getElementById('resultModal'));
    resultModal.show();
  }



  class DomNode {
      constructor(s) {
          this.node = s;
      }
      addClass(s) {
          this.isValidNode() && this.node.classList.add(s);
      }
      removeClass(s) {
          this.isValidNode() && this.node.classList.remove(s);
      }
      toggleClass(s) {
          this.isValidNode() && this.node.classList.toggle(s);
      }
      hasClass(s) {
          this.isValidNode() && this.node.classList.contains(s);
      }
      data(s) {
          if (this.isValidNode())
              try {
                  return JSON.parse(this.node.dataset[this.camelize(s)])
              } catch (t) {
                  return this.node.dataset[this.camelize(s)]
              }
          return null
      }
      attr(s) {
          return this.isValidNode() && this.node[s]
      }
      setAttribute(s, t) {
          this.isValidNode() && this.node.setAttribute(s, t);
      }
      removeAttribute(s) {
          this.isValidNode() && this.node.removeAttribute(s);
      }
      setProp(s, t) {
          this.isValidNode() && (this.node[s] = t);
      }
      on(s, t) {
          this.isValidNode() && this.node.addEventListener(s, t);
      }
      isValidNode() {
          return !!this.node
      }
      camelize(s) {
          const t = s.replace(/[-_\s.]+(.)?/g, ((s,t)=>t ? t.toUpperCase() : ""));
          return `${t.substr(0, 1).toLowerCase()}${t.substr(1)}`
      }
  }

  const elementMap = new Map;
  class BulkSelect {
      constructor(e, t) {
          this.element = e,
          this.option = {
              displayNoneClassName: "d-none",
              ...t
          },
          elementMap.set(this.element, this);
      }
      static getInstance(e) {
          return elementMap.has(e) ? elementMap.get(e) : null
      }
      init() {
          this.attachNodes(),
          this.clickBulkCheckbox(),
          this.clickRowCheckbox();
      }

      getSelectedRows() {
        const selectedRows = Array.from(this.bulkSelectRows).filter((row) => row.checked).map((row) => {
            const checkboxData = getData(row, "bulk-select-row");
            delete checkboxData.duration;
            delete checkboxData.startTime;
            delete checkboxData.endTime;
            delete checkboxData.maxThreads;
            return checkboxData;
        });

        return selectedRows;
    }
      attachNodes() {
          const {body: e, actions: t, replacedElement: s} = getData(this.element, "bulk-select");
          this.actions = new DomNode(document.getElementById(t)),
          this.replacedElement = new DomNode(document.getElementById(s)),
          this.bulkSelectRows = document.getElementById(e).querySelectorAll("[data-bulk-select-row]");

      }
      attachRowNodes(e) {
          this.bulkSelectRows = e;
      }
      clickBulkCheckbox() {
          this.element.addEventListener("click", (()=>{
              if ("indeterminate" === this.element.indeterminate)
                  return this.actions.addClass(this.option.displayNoneClassName),
                  this.replacedElement.removeClass(this.option.displayNoneClassName),
                  this.removeBulkCheck(),
                  void this.bulkSelectRows.forEach((e=>{
                      const t = new DomNode(e);
                      t.checked = !1,
                      t.setAttribute("checked", !1);
                  }
                  ));
              this.toggleDisplay(),
              this.bulkSelectRows.forEach((e=>{
                  e.checked = this.element.checked;
              }
              ));
          }
          ));
      }
      clickRowCheckbox() {
          this.bulkSelectRows.forEach((e=>{
              new DomNode(e).on("click", (()=>{
                  "indeterminate" !== this.element.indeterminate && (this.element.indeterminate = !0,
                  this.element.setAttribute("indeterminate", "indeterminate"),
                  this.element.checked = !0,
                  this.element.setAttribute("checked", !0),
                  this.actions.removeClass(this.option.displayNoneClassName),
                  this.replacedElement.addClass(this.option.displayNoneClassName)),
                  [...this.bulkSelectRows].every((e=>e.checked)) && (this.element.indeterminate = !1,
                  this.element.setAttribute("indeterminate", !1)),
                  [...this.bulkSelectRows].every((e=>!e.checked)) && (this.removeBulkCheck(),
                  this.toggleDisplay());
              }
              ));
          }
          ));
      }
      removeBulkCheck() {
          this.element.indeterminate = !1,
          this.element.removeAttribute("indeterminate"),
          this.element.checked = !1,
          this.element.setAttribute("checked", !1);
      }
      toggleDisplay() {
          this.actions.toggleClass(this.option.displayNoneClassName),
          this.replacedElement.toggleClass(this.option.displayNoneClassName);
      }
  }
  const bulkSelectInit = ()=>{
      const e = document.querySelectorAll("[data-bulk-select]");
      e.length && e.forEach((e=>{
          new BulkSelect(e).init();
      }
      ));
  };

  const togglePaginationButtonDisable = (button, disabled) => {
      button.disabled = disabled;
      button.classList[disabled ? 'add' : 'remove']('disabled');
  };

  const listInit = () => {
      const { getData } = window.perforge.utils;
      if (window.List) {
        const lists = document.querySelectorAll('[data-list]');

        if (lists.length) {
          lists.forEach(el => {
            const bulkSelect = el.querySelector('[data-bulk-select]');

            let options = getData(el, 'list');

            if (options.pagination) {
              options = {
                ...options,
                pagination: {
                  item: `<li><button class='page' type='button'></button></li>`,
                  ...options.pagination
                }
              };
            }

            const paginationButtonNext = el.querySelector(
              '[data-list-pagination="next"]'
            );
            const paginationButtonPrev = el.querySelector(
              '[data-list-pagination="prev"]'
            );
            const viewAll = el.querySelector('[data-list-view="*"]');
            const viewLess = el.querySelector('[data-list-view="less"]');
            const listInfo = el.querySelector('[data-list-info]');
            const listFilter = document.querySelector('[data-list-filter]');

            // Handle List.js initialization with proper error handling
            try {
              // Add a dummy row if needed - List.js requires at least one item during initialization
              const listBody = el.querySelector('.list');
              let dummyRowAdded = false;

              if (listBody && listBody.children.length === 0) {
                const dummyRow = document.createElement('tr');
                dummyRow.id = 'dummy-list-row';
                dummyRow.style.display = 'none';

                // Add cells with appropriate classes based on valueNames
                if (options.valueNames && Array.isArray(options.valueNames)) {
                  options.valueNames.forEach(name => {
                    const cell = document.createElement('td');
                    cell.className = name;
                    cell.textContent = 'dummy';
                    dummyRow.appendChild(cell);
                  });
                } else {
                  // Fallback if no valueNames
                  dummyRow.innerHTML = '<td>dummy</td>';
                }

                listBody.appendChild(dummyRow);
                dummyRowAdded = true;
              }

              // Initialize List.js
              const list = new List(el, options);

              // Store the list instance on the element for later access
              el.List = list;

              // Remove the dummy row if we added one
              if (dummyRowAdded) {
                const dummyRow = listBody.querySelector('#dummy-list-row');
                if (dummyRow) {
                  dummyRow.remove();
                }

                // Reset the items array after removing the dummy
                if (list.items && list.items.length === 1) {
                  list.items = [];
                  list.visibleItems = [];
                  list.matchingItems = [];
                }
              }

            } catch (error) {
              console.error('List.js initialization error:', error);
              return; // Exit if initialization fails
            }

            // Get the list instance from the element
            const list = el.List;
            if (!list) return; // Skip the rest if list initialization failed

            // -------fallback-----------

            list.on('updated', item => {
              const fallback =
                el.querySelector('.fallback') ||
                document.getElementById(options.fallback);

              if (fallback) {
                if (item.matchingItems.length === 0) {
                  fallback.classList.remove('d-none');
                } else {
                  fallback.classList.add('d-none');
                }
              }
            });

            // ---------------------------------------

            const totalItem = list.items.length;
            const itemsPerPage = list.page;
            const btnDropdownClose = list.listContainer.querySelector('.btn-close');
            let pageQuantity = Math.ceil(totalItem / itemsPerPage);
            let numberOfcurrentItems = list.visibleItems.length;
            let pageCount = 1;

            btnDropdownClose &&
              btnDropdownClose.addEventListener('search.close', () => {
                list.fuzzySearch('');
              });

            const updateListControls = () => {
              listInfo &&
                (listInfo.innerHTML = `${list.i} to ${list.i + list.visibleItems.length - 1} <span> Items of </span>${totalItem}`);

              paginationButtonPrev &&
                togglePaginationButtonDisable(
                  paginationButtonPrev,
                  list.i === 1
                );
              paginationButtonNext &&
                togglePaginationButtonDisable(
                  paginationButtonNext,
                  list.i + list.visibleItems.length >= totalItem
                );
            };

            // List info
            updateListControls();

            list.on('updated', item => {
              updateListControls();
            });

            if (paginationButtonNext) {
              paginationButtonNext.addEventListener('click', e => {
                e.preventDefault();
                const nextInitialIndex = list.i + itemsPerPage;
                if (nextInitialIndex <= list.size()) {
                  list.show(nextInitialIndex, itemsPerPage);
                }
              });
            }

            if (paginationButtonPrev) {
              paginationButtonPrev.addEventListener('click', e => {
                e.preventDefault();
                const prevItem = list.i - itemsPerPage;
                if (prevItem > 0) {
                  list.show(prevItem, itemsPerPage);
                }
              });
            }

            const toggleViewBtn = () => {
              viewLess.classList.toggle('d-none');
              viewAll.classList.toggle('d-none');
            };

            if (viewAll) {
              viewAll.addEventListener('click', () => {
                list.show(1, totalItem);
                pageQuantity = 1;
                pageCount = 1;
                numberOfcurrentItems = totalItem;
                updateListControls();
                toggleViewBtn();
              });
            }
            if (viewLess) {
              viewLess.addEventListener('click', () => {
                list.show(1, itemsPerPage);
                pageQuantity = Math.ceil(totalItem / itemsPerPage);
                pageCount = 1;
                numberOfcurrentItems = list.visibleItems.length;
                updateListControls();
                toggleViewBtn();
              });
            }
            // numbering pagination
            if (options.pagination) {
              el.querySelector('.pagination').addEventListener('click', e => {
                if (e.target.classList[0] === 'page') {
                  const pageNum = Number(e.target.getAttribute('data-i'));
                  if (pageNum) {
                    list.show(
                      itemsPerPage * (pageNum - 1) + 1,
                      numberOfcurrentItems
                    );
                    numberOfcurrentItems =
                      list.visibleItems.length < itemsPerPage
                        ? itemsPerPage * (pageNum - 1) + list.visibleItems.length
                        : itemsPerPage * pageNum;
                    pageCount = pageNum;
                    updateListControls();
                  }
                }
              });
            }
            //filter
            if (options.filter) {
              const { key } = options.filter;
              listFilter.addEventListener('change', e => {
                list.filter(item => {
                  if (e.target.value === '') {
                    return true;
                  }
                  return item
                    .values()
                    [key].toLowerCase()
                    .includes(e.target.value.toLowerCase());
                });
              });
            }

            //bulk-select
            if (bulkSelect) {
              const bulkSelectInstance = window.perforge.BulkSelect.getInstance(bulkSelect);
              bulkSelectInstance.attachRowNodes(
                list.items.map(item =>
                  item.elm.querySelector('[data-bulk-select-row]')
                )
              );

              bulkSelect.addEventListener('change', () => {
                if (list) {
                  if (bulkSelect.checked) {
                    list.items.forEach(item => {
                      item.elm.querySelector(
                        '[data-bulk-select-row]'
                      ).checked = true;
                    });
                  } else {
                    list.items.forEach(item => {
                      item.elm.querySelector(
                        '[data-bulk-select-row]'
                      ).checked = false;
                    });
                  }
                }
              });
            }
          });
        }
      }
  };

  var utils = {
    listInit: listInit,
    validateForm: validateForm,
    sendPostRequest: sendPostRequest,
    sendGetRequest: sendGetRequest,
    docReady: docReady,
    camelize: camelize,
    getData: getData,
    hasClass: hasClass,
    addClass: addClass,
    removeClass: removeClass,
    setCookie: setCookie,
    getCookie: getCookie,
    getRandomNumber: getRandomNumber
  };

  docReady(bulkSelectInit),
  docReady(listInit),
  docReady(() => {
    // DOM Elements
    const selectedRowsBtn = document.querySelector('[data-selected-rows]');
    const selectedAction = document.getElementById('selectedAction');
    const showApiBtn = document.getElementById('show-api');
    const selectedDb = document.getElementById('dataSourceId');
    const selectedTemplateGroup = document.getElementById('templateGroupName');
    const spinner = document.getElementById("spinner-apply");
    const spinnerText = document.getElementById("spinner-apply-text");

    // Utility Functions
    const getCookieValue = (name) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      return parts.length === 2 ? parts.pop().split(';').shift() : null;
    };

    const copyToClipboard = async (text) => {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          showResultModal(`API request copied to clipboard!`, text);
        } else {
          // Fallback for browsers that do not support navigator.clipboard
          const textarea = document.createElement('textarea');
          textarea.value = text;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          showResultModal(`API request copied to clipboard!`, text);
        }
      } catch (err) {
        console.error('Error copying to clipboard: ', err);
      }
    };

    const get_tests_data = () => {
      const bulkSelectEl = document.getElementById('bulk-select-example');
      const bulkSelectInstance = window.perforge.BulkSelect.getInstance(bulkSelectEl);
      const transformedList = bulkSelectInstance.getSelectedRows();
      const selectedRows = {};
      const output = JSON.parse(selectedAction.value.toString());

      if (transformedList.length === 0) {
        showResultModal("Please choose at least one test.");
        return null;
      }

      if (output.type === "none") {
        showResultModal("Please choose an action.");
        return null;
      }

      // Validate templates before filtering
      if(output.type !== "delete"){
        for (const item of transformedList) {
          if (!item.template_id || item.template_id === "no data") {
            showResultModal(`${item.test_title} has an empty template.`);
            return null;
          }
        }
      }

      // Filter db_id to only include required fields (id and source_type)
      const fullDbId = JSON.parse(selectedDb.value);
      const dbId = {
        id: fullDbId.id,
        source_type: fullDbId.source_type
      };

      // Filter each test object to include required fields, preserving baseline_test_title
      selectedRows["tests"] = transformedList.map(test => {
        const newTest = {
          test_title: test.test_title,
          template_id: test.template_id,
          db_id: dbId
        };
        if (test.baseline_test_title && test.baseline_test_title !== "no data") {
          newTest.baseline_test_title = test.baseline_test_title;
        }
        return newTest;
      });

      selectedRows["output_id"] = (output.type === "pdf_report" || output.type === "delete") ? output.type : output.id;

      // Add integration_type to the request data if it exists in the output object
      if (output.integration_type) {
        selectedRows["integration_type"] = output.integration_type;
      }

      // Add selected theme for PDF reports
      if (output.type === 'pdf_report') {
        const theme = localStorage.getItem('theme') || 'dark';
        selectedRows['theme'] = theme;
      }

      if (selectedTemplateGroup.value !== "") {
        selectedRows["template_group"] = selectedTemplateGroup.value;
      }

      return selectedRows;
    };

    const handleRequest = async (url, data, requestType) => {
      try {
        spinner.style.display = "inline-block";
        spinnerText.style.display = "none";

        if (requestType === 'download') {
          await sendDownloadRequest(url, data);
        } else if (requestType === 'delete') {
          // For delete operations, use the API client directly
          if (url === '/generate') {
            const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
            const response = await apiClient.tests.generateReport(parsedData);
            if (response.status === 'success') {
              showFlashMessage('Tests deleted successfully', 'success');
              location.reload();
            } else {
              showFlashMessage(response.message || 'Failed to delete tests', 'error');
            }
          } else {
            await sendPostRequest(url, data);
          }
        } else {
          await sendPostRequestReport(url, data);
        }
      } finally {
        spinner.style.display = "none";
        spinnerText.style.display = "";
      }
    };

    // Event Listeners
    if (selectedRowsBtn) {
      selectedRowsBtn.addEventListener('click', async () => {
        const selectedRows = get_tests_data();
        if (!selectedRows) return;

        const selectedActionValue = JSON.parse(selectedAction.value.toString());
        const requestType = selectedActionValue.type === "pdf_report" ? 'download' : selectedActionValue.type === "delete" ? 'delete' : 'report';

        await handleRequest('/generate', JSON.stringify(selectedRows), requestType);
      });
    }

    if (showApiBtn) {
      showApiBtn.addEventListener('click', () => {
        const selectedRows = get_tests_data();
        if (!selectedRows) return;

        const projectCookieValue = getCookieValue('project');
        const baseUrl = `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}`;

        // Use the new API endpoint
        const post_request = `
curl -k --fail-with-body --request POST \\
--url ${baseUrl}/api/v1/reports \\
-H "Content-Type: application/json" \\
-H "Cookie: project=${projectCookieValue}" \\
--data '${JSON.stringify(selectedRows, null, 2)}'
`;

        copyToClipboard(post_request.trim());
      });
    }
  });
  var perforge = {
      utils: utils,
      BulkSelect: BulkSelect
  };

  return perforge;
}
));
